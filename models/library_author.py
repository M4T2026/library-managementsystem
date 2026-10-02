# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LibraryAuthor(models.Model):
    _name = 'library.author'
    _description = 'Book Author'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Author Name', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    website = fields.Char(string='Website')
    biography = fields.Html(string='Biography')
    nationality = fields.Many2one('res.country', string='Nationality')
    birth_date = fields.Date(string='Date of Birth')
    death_date = fields.Date(string='Date of Death')
    image = fields.Image(string='Photo', max_width=256, max_height=256)
    book_ids = fields.Many2many(
        'library.book', 'library_book_author_rel', 'author_id', 'book_id',
        string='Books'
    )
    book_count = fields.Integer(string='Books', compute='_compute_book_count')
    active = fields.Boolean(string='Active', default=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')

    @api.depends('book_ids')
    def _compute_book_count(self):
        for author in self:
            author.book_count = len(author.book_ids)

    def action_view_books(self):
        return {
            'name': f'Books by {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,kanban,form',
            'domain': [('author_ids', 'in', self.id)],
            'context': {'default_author_ids': [(4, self.id)]},
        }
