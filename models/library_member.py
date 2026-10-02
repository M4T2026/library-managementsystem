# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'
    _rec_name = 'name'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Identity ─────────────────────────────────────────────────────────────
    name = fields.Char(string='Full Name', required=True, tracking=True)
    member_ref = fields.Char(
        string='Member ID', default=lambda self: _('New'),
        readonly=True, copy=False, index=True
    )
    partner_id = fields.Many2one('res.partner', string='Related Contact')
    image = fields.Image(string='Photo', max_width=256, max_height=256)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age')
    id_type = fields.Selection([
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('student_card', 'Student Card'),
        ('employee_id', 'Employee ID'),
    ], string='ID Type', default='national_id')
    id_number = fields.Char(string='ID Number')

    # ── Contact ──────────────────────────────────────────────────────────────
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile')
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip = fields.Char(string='ZIP')

    # ── Membership ───────────────────────────────────────────────────────────
    membership_type = fields.Selection([
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('student', 'Student'),
        ('senior', 'Senior'),
        ('corporate', 'Corporate'),
    ], string='Membership Type', default='standard', tracking=True)
    membership_start = fields.Date(string='Membership Start', default=fields.Date.today)
    membership_end = fields.Date(string='Membership Expiry', tracking=True)
    max_books_allowed = fields.Integer(
        string='Max Books Allowed', default=3,
        compute='_compute_max_books', store=True
    )
    fine_balance = fields.Float(
        string='Outstanding Fine', compute='_compute_fine_balance', store=True
    )
    barcode = fields.Char(string='Member Card Barcode', index=True)

    # ── State ────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('blacklisted', 'Blacklisted'),
    ], string='Status', default='active', tracking=True)

    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')

    # ── Stats ────────────────────────────────────────────────────────────────
    borrowing_ids = fields.One2many('library.borrowing', 'member_id', string='Borrowings')
    current_borrowing_count = fields.Integer(
        string='Current Borrows', compute='_compute_borrowing_stats'
    )
    total_borrowing_count = fields.Integer(
        string='Total Borrows', compute='_compute_borrowing_stats'
    )
    overdue_count = fields.Integer(
        string='Overdue', compute='_compute_borrowing_stats'
    )

    # ── Compute Methods ──────────────────────────────────────────────────────
    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for member in self:
            if member.date_of_birth:
                member.age = today.year - member.date_of_birth.year - (
                    (today.month, today.day) < (member.date_of_birth.month, member.date_of_birth.day)
                )
            else:
                member.age = 0

    @api.depends('membership_type')
    def _compute_max_books(self):
        limits = {
            'standard': 3,
            'premium': 10,
            'student': 5,
            'senior': 4,
            'corporate': 15,
        }
        for member in self:
            member.max_books_allowed = limits.get(member.membership_type, 3)

    def _compute_borrowing_stats(self):
        for member in self:
            borrows = member.borrowing_ids
            member.total_borrowing_count = len(borrows)
            member.current_borrowing_count = len(borrows.filtered(
                lambda b: b.state in ('borrowed', 'overdue')
            ))
            member.overdue_count = len(borrows.filtered(lambda b: b.state == 'overdue'))

    @api.depends('borrowing_ids.fine_amount', 'borrowing_ids.fine_paid')
    def _compute_fine_balance(self):
        for member in self:
            total = sum(member.borrowing_ids.filtered(
                lambda b: not b.fine_paid
            ).mapped('fine_amount'))
            member.fine_balance = total

    # ── ORM Overrides ─────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('member_ref', _('New')) == _('New'):
                vals['member_ref'] = self.env['ir.sequence'].next_by_code('library.member') or _('New')
        return super().create(vals_list)

    @api.constrains('membership_end')
    def _check_membership_end(self):
        for member in self:
            if member.membership_end and member.membership_start:
                if member.membership_end < member.membership_start:
                    raise ValidationError(_('Membership expiry date cannot be before start date.'))

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_activate(self):
        self.write({'state': 'active'})

    def action_blacklist(self):
        self.write({'state': 'blacklisted'})

    def action_renew_membership(self):
        return {
            'name': _('Renew Membership'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.member',
            'res_id': self.id,
            'view_mode': 'form',
        }

    def action_view_borrowings(self):
        return {
            'name': _('Borrowing History'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_print_member_card(self):
        return self.env.ref('library_management.action_report_member_card').report_action(self)
