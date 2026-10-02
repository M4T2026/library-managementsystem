# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date


class ReturnBookWizard(models.TransientModel):
    _name = 'return.book.wizard'
    _description = 'Return Book Wizard'

    member_id = fields.Many2one(
        'library.member', string='Member',
        domain=[('state', 'in', ['active', 'suspended'])]
    )
    borrowing_id = fields.Many2one(
        'library.borrowing', string='Borrowing',
        domain="[('state', 'in', ['borrowed', 'overdue']), ('member_id', '=?', member_id)]",
        required=True
    )
    book_id = fields.Many2one(
        'library.book', related='borrowing_id.book_id', readonly=True
    )
    borrow_date = fields.Date(related='borrowing_id.borrow_date', readonly=True)
    due_date = fields.Date(related='borrowing_id.due_date', readonly=True)
    return_date = fields.Date(string='Return Date', default=fields.Date.today, required=True)
    condition = fields.Selection([
        ('good', 'Good Condition'),
        ('minor_damage', 'Minor Damage'),
        ('major_damage', 'Major Damage'),
        ('lost', 'Book Lost'),
    ], string='Book Condition', default='good', required=True)
    overdue_days = fields.Integer(string='Overdue Days', compute='_compute_fine')
    calculated_fine = fields.Float(string='Calculated Fine', compute='_compute_fine')
    additional_fine = fields.Float(string='Additional Fine (Damage/Lost)')
    total_fine = fields.Float(string='Total Fine', compute='_compute_total_fine')
    waive_fine = fields.Boolean(string='Waive Fine')
    notes = fields.Text(string='Notes')

    @api.depends('borrowing_id', 'return_date')
    def _compute_fine(self):
        today = date.today()
        for rec in self:
            if rec.borrowing_id and rec.return_date and rec.due_date:
                overdue = max((rec.return_date - rec.due_date).days, 0)
                rec.overdue_days = overdue
                rec.calculated_fine = overdue * rec.borrowing_id.fine_per_day
            else:
                rec.overdue_days = 0
                rec.calculated_fine = 0

    @api.depends('calculated_fine', 'additional_fine', 'condition')
    def _compute_total_fine(self):
        for rec in self:
            extra = rec.additional_fine
            if rec.condition == 'lost':
                extra = max(rec.book_id.price or 100.0, extra)
            rec.total_fine = rec.calculated_fine + extra

    def action_return(self):
        self.ensure_one()
        b = self.borrowing_id
        if b.state not in ('borrowed', 'overdue'):
            raise UserError(_('This book is not currently borrowed.'))

        fine = 0 if self.waive_fine else self.total_fine
        b.write({
            'state': 'returned' if self.condition != 'lost' else 'lost',
            'return_date': self.return_date,
            'fine_amount': fine,
            'fine_paid': fine == 0,
        })
        b.book_id._compute_available_copies()

        if self.condition == 'lost':
            b.book_id.write({'state': 'lost'})

        if fine > 0:
            # Create a Fine record
            self.env['library.fine'].create({
                'member_id': b.member_id.id,
                'borrowing_id': b.id,
                'amount': fine,
                'reason': 'overdue' if self.overdue_days > 0 else 'damage',
                'notes': self.notes,
            })
            b.message_post(body=_(
                'Book returned with fine: %.2f (overdue days: %d, condition: %s).'
            ) % (fine, self.overdue_days, self.condition))

        return {
            'name': _('Borrowing'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'res_id': b.id,
            'view_mode': 'form',
            'target': 'current',
        }
