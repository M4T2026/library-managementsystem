from odoo import api, fields, models


class LibraryAuthor(models.Model):
    _name = 'library.author'
    _description = 'Library Author'
    _order = 'name'

    name = fields.Char(required=True)
    biography = fields.Text()
    image = fields.Image(max_width=256, max_height=256)
    book_ids = fields.Many2many(
        'library.book', 'library_book_author_rel', 'author_id', 'book_id', string='Books')
    book_count = fields.Integer(compute='_compute_book_count')

    @api.depends('book_ids')
    def _compute_book_count(self):
        for author in self:
            author.book_count = len(author.book_ids)


class LibraryCategory(models.Model):
    _name = 'library.category'
    _description = 'Book Category'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer()
    book_ids = fields.One2many('library.book', 'category_id', string='Books')
    book_count = fields.Integer(compute='_compute_book_count')

    _name_uniq = models.Constraint('UNIQUE(name)', 'Category name must be unique.')

    @api.depends('book_ids')
    def _compute_book_count(self):
        for categ in self:
            categ.book_count = len(categ.book_ids)


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Title', required=True, tracking=True)
    isbn = fields.Char(string='ISBN', copy=False, tracking=True)
    author_ids = fields.Many2many(
        'library.author', 'library_book_author_rel', 'book_id', 'author_id', string='Authors')
    category_id = fields.Many2one('library.category', string='Category', tracking=True)
    publisher = fields.Char()
    publication_year = fields.Integer()
    language = fields.Char(default='English')
    pages = fields.Integer()
    price = fields.Monetary(string='Replacement Price', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    cover = fields.Image(max_width=512, max_height=512)
    description = fields.Html()
    active = fields.Boolean(default=True)

    copy_ids = fields.One2many('library.book.copy', 'book_id', string='Copies')
    copy_count = fields.Integer(compute='_compute_copy_stats', store=True)
    available_count = fields.Integer(compute='_compute_copy_stats', store=True)
    loan_count = fields.Integer(compute='_compute_loan_count')

    _isbn_uniq = models.Constraint('UNIQUE(isbn)', 'This ISBN already exists.')

    @api.depends('copy_ids.state', 'copy_ids.active')
    def _compute_copy_stats(self):
        for book in self:
            copies = book.copy_ids
            book.copy_count = len(copies)
            book.available_count = len(copies.filtered(lambda c: c.state == 'available'))

    def _compute_loan_count(self):
        data = dict(self.env['library.loan']._read_group(
            [('book_id', 'in', self.ids)], ['book_id'], ['__count']))
        for book in self:
            book.loan_count = data.get(book, 0)

    def action_add_copy(self):
        self.ensure_one()
        self.env['library.book.copy'].create({'book_id': self.id})
        return True

    def action_view_loans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'library.loan',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
        }


class LibraryBookCopy(models.Model):
    _name = 'library.book.copy'
    _description = 'Book Copy'
    _rec_name = 'barcode'
    _order = 'book_id, barcode'

    book_id = fields.Many2one('library.book', required=True, ondelete='cascade', index=True)
    barcode = fields.Char(copy=False, index=True, readonly=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('maintenance', 'In Maintenance'),
        ('lost', 'Lost'),
    ], default='available', required=True)
    acquisition_date = fields.Date(default=fields.Date.context_today)
    notes = fields.Char()
    active = fields.Boolean(default=True)
    loan_ids = fields.One2many('library.loan', 'copy_id', string='Loans')

    _barcode_uniq = models.Constraint('UNIQUE(barcode)', 'Barcode must be unique.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('barcode'):
                vals['barcode'] = self.env['ir.sequence'].next_by_code('library.book.copy')
        return super().create(vals_list)

    @api.depends('book_id.name', 'barcode')
    def _compute_display_name(self):
        for copy in self:
            copy.display_name = f"{copy.book_id.name or ''} [{copy.barcode or 'New'}]"
