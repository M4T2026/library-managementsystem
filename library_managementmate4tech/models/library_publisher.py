# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LibraryPublisher(models.Model):
    _name = 'library.publisher'
    _description = 'Book Publisher'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Publisher Name', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    website = fields.Char(string='Website')
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one(
        'res.country.state', string='State',
        domain="[('country_id', '=', country_id)]"
    )
    zip = fields.Char(string='ZIP')
    image = fields.Image(string='Logo', max_width=256, max_height=256)
    book_count = fields.Integer(string='Books', compute='_compute_book_count')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)

    def _compute_book_count(self):
        for publisher in self:
            publisher.book_count = self.env['library.book'].search_count(
                [('publisher_id', '=', publisher.id)]
            )

    def action_view_books(self):
        return {
            'name': f'Books by {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,kanban,form',
            'domain': [('publisher_id', '=', self.id)],
            'context': {'default_publisher_id': self.id},
        }
