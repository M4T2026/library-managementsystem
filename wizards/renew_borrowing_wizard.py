# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta


class RenewBorrowingWizard(models.TransientModel):
    _name = 'renew.borrowing.wizard'
    _description = 'Renew Borrowing Wizard'

    borrowing_id = fields.Many2one(
        'library.borrowing', string='Borrowing',
        domain=[('state', 'in', ['borrowed', 'overdue'])],
        required=True
    )
    member_id = fields.Many2one(
        'library.member', related='borrowing_id.member_id', readonly=True
    )
    book_id = fields.Many2one(
        'library.book', related='borrowing_id.book_id', readonly=True
    )
    current_due_date = fields.Date(related='borrowing_id.due_date', readonly=True)
    renewal_count = fields.Integer(related='borrowing_id.renewal_count', readonly=True)
    max_renewals = fields.Integer(related='borrowing_id.max_renewals', readonly=True)
    extra_days = fields.Integer(string='Extend By (Days)', default=7, required=True)
    new_due_date = fields.Date(string='New Due Date', compute='_compute_new_due_date')
    notes = fields.Text(string='Notes')

    @api.depends('borrowing_id', 'extra_days')
    def _compute_new_due_date(self):
        for rec in self:
            if rec.borrowing_id and rec.extra_days:
                base = rec.borrowing_id.due_date or fields.Date.today()
                rec.new_due_date = base + timedelta(days=rec.extra_days)
            else:
                rec.new_due_date = False

    def action_renew(self):
        self.ensure_one()
        b = self.borrowing_id
        if b.renewal_count >= b.max_renewals:
            raise UserError(_(
                'Maximum renewal limit (%d) has been reached for this borrowing.'
            ) % b.max_renewals)
        if b.state not in ('borrowed', 'overdue'):
            raise UserError(_('Can only renew active borrowings.'))

        b.write({
            'due_date': self.new_due_date,
            'renewal_count': b.renewal_count + 1,
            'state': 'borrowed',  # reset overdue status if any
        })
        b.message_post(body=_(
            'Borrowing renewed by %s. New due date: %s. Renewal #%d.'
        ) % (self.env.user.name, self.new_due_date, b.renewal_count))

        return {
            'name': _('Borrowing'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'res_id': b.id,
            'view_mode': 'form',
            'target': 'current',
        }
