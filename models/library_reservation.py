# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LibraryReservation(models.Model):
    _name = 'library.reservation'
    _description = 'Book Reservation'
    _rec_name = 'name'
    _order = 'reservation_date desc'
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
        'library.book', string='Book', required=True, tracking=True
    )
    reservation_date = fields.Date(
        string='Reservation Date', default=fields.Date.today, required=True
    )
    expiry_date = fields.Date(string='Expiry Date', required=True)
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('reserved', 'Reserved'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], string='Status', default='reserved', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('library.reservation') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.book_id.available_copies < 1:
                raise UserError(_('No copies available to confirm this reservation.'))
            rec.state = 'confirmed'

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        for rec in self:
            rec.book_id._compute_available_copies()

    def action_convert_to_borrowing(self):
        self.ensure_one()
        borrowing = self.env['library.borrowing'].create({
            'member_id': self.member_id.id,
            'book_id': self.book_id.id,
            'borrow_date': fields.Date.today(),
        })
        self.state = 'confirmed'
        return {
            'name': _('Borrowing'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'res_id': borrowing.id,
            'view_mode': 'form',
        }
