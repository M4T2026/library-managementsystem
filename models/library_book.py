# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _rec_name = 'name'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ── Basic Info ──────────────────────────────────────────────────────────
    name = fields.Char(string='Title', required=True, tracking=True, index=True)
    isbn = fields.Char(string='ISBN', index=True)
    isbn13 = fields.Char(string='ISBN-13')
    barcode = fields.Char(string='Barcode', index=True)
    ref = fields.Char(
        string='Reference', default=lambda self: _('New'),
        readonly=True, copy=False, index=True
    )
    image = fields.Image(string='Cover Image', max_width=512, max_height=512)
    image_small = fields.Image(string='Cover (Small)', related='image',
                                max_width=128, max_height=128, store=True)
    description = fields.Html(string='Description')
    short_description = fields.Text(string='Short Description')
    notes = fields.Text(string='Internal Notes')

    # ── Classification ───────────────────────────────────────────────────────
    category_id = fields.Many2one(
        'library.category', string='Category', required=True, tracking=True,
        index=True
    )
    author_ids = fields.Many2many(
        'library.author', 'library_book_author_rel', 'book_id', 'author_id',
        string='Authors', required=True
    )
    publisher_id = fields.Many2one('library.publisher', string='Publisher', tracking=True)
    language = fields.Selection([
        ('en', 'English'), ('ar', 'Arabic'), ('fr', 'French'),
        ('de', 'German'), ('es', 'Spanish'), ('ur', 'Urdu'),
        ('zh', 'Chinese'), ('ja', 'Japanese'), ('other', 'Other'),
    ], string='Language', default='en')
    edition = fields.Char(string='Edition')
    pages = fields.Integer(string='Pages')
    publication_year = fields.Integer(string='Publication Year')
    tag_ids = fields.Many2many('library.tag', string='Tags')

    # ── Inventory ───────────────────────────────────────────────────────────
    total_copies = fields.Integer(string='Total Copies', default=1, tracking=True)
    available_copies = fields.Integer(
        string='Available Copies', compute='_compute_available_copies', store=True
    )
    borrowed_copies = fields.Integer(
        string='Borrowed Copies', compute='_compute_available_copies', store=True
    )
    reserved_copies = fields.Integer(
        string='Reserved Copies', compute='_compute_available_copies', store=True
    )
    location = fields.Char(string='Shelf Location')
    rack_number = fields.Char(string='Rack Number')

    # ── Pricing ─────────────────────────────────────────────────────────────
    price = fields.Float(string='Price', digits=(10, 2))
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    # ── State ───────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('reserved', 'Reserved'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', default='available', tracking=True, compute='_compute_state', store=True)

    active = fields.Boolean(string='Active', default=True)

    # ── Relations ───────────────────────────────────────────────────────────
    borrowing_ids = fields.One2many('library.borrowing', 'book_id', string='Borrowings')
    reservation_ids = fields.One2many('library.reservation', 'book_id', string='Reservations')
    total_borrow_count = fields.Integer(
        string='Total Borrows', compute='_compute_total_borrow_count', store=True
    )

    # ── Compute Methods ─────────────────────────────────────────────────────
    @api.depends('borrowing_ids', 'borrowing_ids.state', 'reservation_ids', 'reservation_ids.state', 'total_copies')
    def _compute_available_copies(self):
        for book in self:
            borrowed = self.env['library.borrowing'].search_count([
                ('book_id', '=', book.id),
                ('state', 'in', ['borrowed', 'overdue']),
            ])
            reserved = self.env['library.reservation'].search_count([
                ('book_id', '=', book.id),
                ('state', '=', 'reserved'),
            ])
            book.borrowed_copies = borrowed
            book.reserved_copies = reserved
            book.available_copies = max(book.total_copies - borrowed - reserved, 0)

    @api.depends('available_copies', 'total_copies', 'borrowed_copies')
    def _compute_state(self):
        for book in self:
            if book.available_copies > 0:
                book.state = 'available'
            elif book.borrowed_copies > 0:
                book.state = 'borrowed'
            else:
                book.state = 'available'

    @api.depends('borrowing_ids')
    def _compute_total_borrow_count(self):
        for book in self:
            book.total_borrow_count = len(book.borrowing_ids)

    # ── ORM Overrides ────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', _('New')) == _('New'):
                vals['ref'] = self.env['ir.sequence'].next_by_code('library.book') or _('New')
        return super().create(vals_list)

    @api.constrains('total_copies')
    def _check_total_copies(self):
        for book in self:
            if book.total_copies < 1:
                raise ValidationError(_('Total copies must be at least 1.'))
            if book.total_copies < book.borrowed_copies:
                raise ValidationError(_(
                    'Total copies cannot be less than currently borrowed copies (%d).'
                ) % book.borrowed_copies)

    def action_mark_lost(self):
        self.write({'state': 'lost'})

    def action_mark_available(self):
        self.write({'state': 'available'})

    def action_view_borrowings(self):
        return {
            'name': _('Borrowings'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id},
        }


class LibraryTag(models.Model):
    _name = 'library.tag'
    _description = 'Book Tag'

    name = fields.Char(string='Tag', required=True)
    color = fields.Integer(string='Color')
