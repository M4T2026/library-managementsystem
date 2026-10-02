# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta


class BorrowBookWizard(models.TransientModel):
    _name = 'borrow.book.wizard'
    _description = 'Issue Book to Member'

    member_id = fields.Many2one(
        'library.member', string='Member', required=True,
        domain=[('state', '=', 'active')]
    )
    book_id = fields.Many2one(
        'library.book', string='Book', required=True,
        domain=[('state', '=', 'available'), ('available_copies', '>', 0)]
    )
    borrow_date = fields.Date(
        string='Borrow Date', required=True, default=fields.Date.today
    )
    due_date = fields.Date(string='Due Date', required=True)
    loan_days = fields.Integer(string='Loan Duration (Days)', default=14)
    fine_per_day = fields.Float(string='Fine Per Day', default=1.0)
    notes = fields.Text(string='Notes')

    # Computed info fields
    member_info = fields.Html(string='Member Info', compute='_compute_member_info')
    book_info = fields.Html(string='Book Info', compute='_compute_book_info')

    @api.onchange('loan_days', 'borrow_date')
    def _onchange_loan_days(self):
        if self.borrow_date and self.loan_days:
            self.due_date = self.borrow_date + timedelta(days=self.loan_days)

    @api.depends('member_id')
    def _compute_member_info(self):
        for rec in self:
            if rec.member_id:
                m = rec.member_id
                current = m.current_borrowing_count
                allowed = m.max_books_allowed
                fine = m.fine_balance
                color = 'green' if current < allowed else 'red'
                rec.member_info = f"""
                    <div class="alert alert-info mb-0 p-2">
                        <b>{m.name}</b> ({m.member_ref})<br/>
                        Membership: <b>{m.membership_type}</b> | Expires: <b>{m.membership_end or 'N/A'}</b><br/>
                        Currently borrowed: <b style="color:{color}">{current}/{allowed}</b>
                        {'<br/><span class="text-danger"><b>⚠ Outstanding fine: ' + str(fine) + '</b></span>' if fine > 0 else ''}
                    </div>
                """
            else:
                rec.member_info = ''

    @api.depends('book_id')
    def _compute_book_info(self):
        for rec in self:
            if rec.book_id:
                b = rec.book_id
                authors = ', '.join(b.author_ids.mapped('name'))
                rec.book_info = f"""
                    <div class="alert alert-info mb-0 p-2">
                        <b>{b.name}</b><br/>
                        Authors: <b>{authors or 'N/A'}</b><br/>
                        Category: <b>{b.category_id.name if b.category_id else 'N/A'}</b><br/>
                        Available copies: <b style="color:green">{b.available_copies}</b>
                    </div>
                """
            else:
                rec.book_info = ''

    def action_borrow(self):
        self.ensure_one()

        # Validations
        if not self.book_id.available_copies:
            raise UserError(_('No copies of "%s" are currently available.') % self.book_id.name)

        if self.member_id.state != 'active':
            raise UserError(_('Member %s is not active.') % self.member_id.name)

        if self.member_id.fine_balance > 0:
            raise UserError(_(
                'Member %s has an outstanding fine of %.2f. '
                'Please clear it before issuing books.'
            ) % (self.member_id.name, self.member_id.fine_balance))

        current_borrows = self.env['library.borrowing'].search_count([
            ('member_id', '=', self.member_id.id),
            ('state', 'in', ['borrowed', 'overdue']),
        ])
        if current_borrows >= self.member_id.max_books_allowed:
            raise UserError(_(
                '%s has reached the maximum borrowing limit (%d books).'
            ) % (self.member_id.name, self.member_id.max_books_allowed))

        # Create borrowing record
        borrowing = self.env['library.borrowing'].create({
            'member_id': self.member_id.id,
            'book_id': self.book_id.id,
            'borrow_date': self.borrow_date,
            'due_date': self.due_date,
            'fine_per_day': self.fine_per_day,
            'notes': self.notes,
            'state': 'borrowed',
            'librarian_id': self.env.user.id,
        })
        borrowing.book_id._compute_available_copies()

        return {
            'name': _('Borrowing'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'res_id': borrowing.id,
            'view_mode': 'form',
            'target': 'current',
        }
