# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class LibraryFine(models.Model):
    _name = 'library.fine'
    _description = 'Library Fine'
    _rec_name = 'name'
    _order = 'date desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Reference', default=lambda self: _('New'),
        readonly=True, copy=False, index=True
    )
    member_id = fields.Many2one('library.member', string='Member', required=True, tracking=True)
    borrowing_id = fields.Many2one('library.borrowing', string='Borrowing', tracking=True)
    book_id = fields.Many2one(
        'library.book', related='borrowing_id.book_id', string='Book', readonly=True
    )
    date = fields.Date(string='Fine Date', default=fields.Date.today, required=True)
    amount = fields.Float(string='Fine Amount', required=True, tracking=True)
    reason = fields.Selection([
        ('overdue', 'Overdue Return'),
        ('damage', 'Book Damage'),
        ('lost', 'Book Lost'),
        ('other', 'Other'),
    ], string='Reason', default='overdue', required=True)
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('waived', 'Waived'),
    ], string='Status', default='unpaid', tracking=True)
    paid_date = fields.Date(string='Paid Date')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.fine') or _('New')
        return super().create(vals_list)

    def action_pay(self):
        self.write({'state': 'paid', 'paid_date': fields.Date.today()})
        for rec in self:
            if rec.borrowing_id:
                rec.borrowing_id.fine_paid = True

    def action_waive(self):
        self.write({'state': 'waived'})
