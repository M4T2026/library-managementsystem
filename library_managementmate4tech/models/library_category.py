# -*- coding: utf-8 -*-
from odoo import api, fields, models


class LibraryCategory(models.Model):
    _name = 'library.category'
    _description = 'Book Category'
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    complete_name = fields.Char(
        string='Complete Name', compute='_compute_complete_name', store=True
    )
    parent_id = fields.Many2one(
        'library.category', string='Parent Category', ondelete='cascade', index=True
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('library.category', 'parent_id', string='Sub Categories')
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)
    book_count = fields.Integer(string='Books', compute='_compute_book_count')
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f'{category.parent_id.complete_name} / {category.name}'
            else:
                category.complete_name = category.name

    def _compute_book_count(self):
        for category in self:
            category.book_count = self.env['library.book'].search_count(
                [('category_id', 'child_of', category.id)]
            )

    def action_view_books(self):
        return {
            'name': 'Books',
            'type': 'ir.actions.act_window',
            'res_model': 'library.book',
            'view_mode': 'list,kanban,form',
            'domain': [('category_id', 'child_of', self.id)],
            'context': {'default_category_id': self.id},
        }
