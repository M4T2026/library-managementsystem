# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Book Borrowing'
    _rec_name = 'name'
    _order = 'borrow_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference', default=lambda self: _('New'),
        readonly=True, copy=False, index=True
    )
    member_id = fields.Many2one(
        'library.member', string='Member', required=True, tracking=True,
        domain=[('state', '=', 'active')]
    )
    book_id = fields.Many2one(
        'library.book', string='Book', required=True, tracking=True,
        domain=[('state', '=', 'available')]
    )
    book_author_ids = fields.Many2many(
        'library.author', related='book_id.author_ids', string='Authors', readonly=True
    )
    book_category_id = fields.Many2one(
        'library.category', related='book_id.category_id', string='Category', readonly=True
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    borrow_date = fields.Date(
        string='Borrow Date', required=True, default=fields.Date.today, tracking=True
    )
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    return_date = fields.Date(string='Return Date', tracking=True)

    # ── Renewal ───────────────────────────────────────────────────────────────
    renewal_count = fields.Integer(string='Renewal Count', default=0)
    max_renewals = fields.Integer(string='Max Renewals', default=2)
    can_renew = fields.Boolean(string='Can Renew', compute='_compute_can_renew')

    # ── Fine ──────────────────────────────────────────────────────────────────
    fine_amount = fields.Float(string='Fine Amount', tracking=True)
    fine_per_day = fields.Float(string='Fine Per Day', default=1.0)
    fine_paid = fields.Boolean(string='Fine Paid', default=False, tracking=True)
    overdue_days = fields.Integer(string='Overdue Days', compute='_compute_overdue_days')

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', 'Draft'),
        ('borrowed', 'Borrowed'),
        ('overdue', 'Overdue'),
        ('returned', 'Returned'),
        ('lost', 'Lost'),
    ], string='Status', default='draft', tracking=True)

    librarian_id = fields.Many2one(
        'res.users', string='Librarian', default=lambda self: self.env.user
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )

    # ── Compute Methods ────────────────────────────────────────────────────────
    @api.depends('renewal_count', 'max_renewals', 'state')
    def _compute_can_renew(self):
        for rec in self:
            rec.can_renew = (
                rec.state == 'borrowed' and
                rec.renewal_count < rec.max_renewals
            )

    @api.depends('due_date', 'return_date', 'state')
    def _compute_overdue_days(self):
        today = date.today()
        for rec in self:
            if rec.state in ('borrowed', 'overdue'):
                end = rec.return_date or today
                delta = (end - rec.due_date).days if rec.due_date else 0
                rec.overdue_days = max(delta, 0)
            elif rec.return_date and rec.due_date:
                delta = (rec.return_date - rec.due_date).days
                rec.overdue_days = max(delta, 0)
            else:
                rec.overdue_days = 0

    @api.onchange('borrow_date', 'member_id')
    def _onchange_borrow_date(self):
        if self.borrow_date:
            loan_days = 14
            self.due_date = self.borrow_date + timedelta(days=loan_days)

    # ── ORM Overrides ──────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.borrowing') or _('New')
        return super().create(vals_list)

    @api.constrains('member_id', 'state')
    def _check_member_book_limit(self):
        for rec in self:
            if rec.state == 'borrowed':
                member = rec.member_id
                current_borrows = self.env['library.borrowing'].search_count([
                    ('member_id', '=', member.id),
                    ('state', 'in', ['borrowed', 'overdue']),
                    ('id', '!=', rec.id),
                ])
                if current_borrows >= member.max_books_allowed:
                    raise ValidationError(_(
                        'Member %s has reached the maximum allowed borrowing limit (%d books).'
                    ) % (member.name, member.max_books_allowed))

    # ── Actions ────────────────────────────────────────────────────────────────
    def action_borrow(self):
        for rec in self:
            if rec.book_id.available_copies < 1:
                raise UserError(_('No copies available for "%s".') % rec.book_id.name)
            if rec.member_id.state != 'active':
                raise UserError(_('Member %s is not active.') % rec.member_id.name)
            if rec.member_id.fine_balance > 0:
                raise UserError(_(
                    'Member %s has an outstanding fine of %.2f. Please clear it first.'
                ) % (rec.member_id.name, rec.member_id.fine_balance))
            rec.write({'state': 'borrowed'})
            rec.book_id._compute_available_copies()
        return True

    def action_return(self):
        today = date.today()
        for rec in self:
            rec.return_date = today
            overdue = max((today - rec.due_date).days, 0) if rec.due_date else 0
            fine = overdue * rec.fine_per_day
            rec.write({
                'state': 'returned',
                'fine_amount': fine,
                'overdue_days': overdue,
            })
            rec.book_id._compute_available_copies()
            if fine > 0:
                rec.message_post(
                    body=_('Book returned with a fine of %.2f for %d overdue days.') % (fine, overdue)
                )
        return True

    def action_mark_lost(self):
        for rec in self:
            rec.write({'state': 'lost'})
            rec.book_id.write({'state': 'lost'})

    def action_mark_overdue(self):
        today = date.today()
        overdue_borrows = self.search([
            ('state', '=', 'borrowed'),
            ('due_date', '<', today),
        ])
        for rec in overdue_borrows:
            overdue_days = (today - rec.due_date).days
            rec.write({
                'state': 'overdue',
                'fine_amount': overdue_days * rec.fine_per_day,
            })

    def action_pay_fine(self):
        for rec in self:
            rec.fine_paid = True

    def action_print_slip(self):
        return self.env.ref('library_management.action_report_borrowing').report_action(self)
