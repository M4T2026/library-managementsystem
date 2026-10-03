from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class LibraryLoan(models.Model):
    _name = 'library.loan'
    _description = 'Library Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'loan_date desc, id desc'

    name = fields.Char(string='Reference', default='New', copy=False, readonly=True)
    member_id = fields.Many2one(
        'library.member', required=True, tracking=True, index=True, ondelete='restrict')
    copy_id = fields.Many2one(
        'library.book.copy', string='Copy', required=True, tracking=True, index=True,
        ondelete='restrict', domain="[('state', '=', 'available')]")
    book_id = fields.Many2one(related='copy_id.book_id', store=True, index=True)
    category_id = fields.Many2one(related='copy_id.book_id.category_id', store=True)
    loan_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    due_date = fields.Date(
        compute='_compute_due_date', store=True, precompute=True, readonly=False,
        required=True, tracking=True)
    return_date = fields.Date(copy=False, readonly=True, tracking=True)
    renew_count = fields.Integer(string='Renewals', default=0, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('borrowed', 'Borrowed'),
        ('overdue', 'Overdue'),
        ('returned', 'Returned'),
        ('lost', 'Lost'),
    ], default='draft', required=True, tracking=True, copy=False, index=True)
    days_late = fields.Integer(compute='_compute_fine', store=True)
    fine_amount = fields.Monetary(compute='_compute_fine', store=True, currency_field='currency_id')
    fine_paid = fields.Boolean(copy=False, tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)
    notes = fields.Text()

    # ------------------------------------------------------------------
    # Configuration helpers (System Parameters: library.*)
    # ------------------------------------------------------------------
    @api.model
    def _get_loan_days(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('library.loan_days', 14))

    @api.model
    def _get_fine_per_day(self):
        return float(self.env['ir.config_parameter'].sudo().get_param('library.fine_per_day', 1.0))

    @api.model
    def _get_max_renewals(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('library.max_renewals', 2))

    # ------------------------------------------------------------------
    # Computes & constraints
    # ------------------------------------------------------------------
    @api.depends('loan_date')
    def _compute_due_date(self):
        days = self._get_loan_days()
        for loan in self:
            if loan.loan_date:
                loan.due_date = loan.loan_date + timedelta(days=days)

    @api.depends('due_date', 'return_date', 'state', 'book_id.price')
    def _compute_fine(self):
        today = fields.Date.context_today(self)
        rate = self._get_fine_per_day()
        for loan in self:
            late = 0
            fine = 0.0
            if loan.state == 'lost':
                fine = loan.book_id.price
            elif loan.state != 'draft' and loan.due_date:
                late = max(((loan.return_date or today) - loan.due_date).days, 0)
                fine = late * rate
            loan.days_late = late
            loan.fine_amount = fine

    @api.constrains('loan_date', 'due_date')
    def _check_dates(self):
        for loan in self:
            if loan.due_date and loan.loan_date and loan.due_date < loan.loan_date:
                raise ValidationError(self.env._("Due date cannot be before the loan date."))

    @api.constrains('copy_id', 'state')
    def _check_single_active_loan(self):
        for loan in self.filtered(lambda l: l.state in ('borrowed', 'overdue')):
            clash = self.search_count([
                ('copy_id', '=', loan.copy_id.id),
                ('state', 'in', ('borrowed', 'overdue')),
                ('id', '!=', loan.id),
            ])
            if clash:
                raise ValidationError(self.env._("This copy is already on loan."))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('library.loan') or 'New'
        return super().create(vals_list)

    def unlink(self):
        if any(loan.state != 'draft' for loan in self):
            raise UserError(self.env._("Only draft loans can be deleted."))
        return super().unlink()

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_borrow(self):
        today = fields.Date.context_today(self)
        for loan in self.filtered(lambda l: l.state == 'draft'):
            member = loan.member_id
            if member.expiry_date < today:
                raise UserError(self.env._("%s's membership has expired.", member.name))
            if member.active_loan_count >= member.max_loans:
                raise UserError(self.env._(
                    "%(member)s has reached the limit of %(max)s loans.",
                    member=member.name, max=member.max_loans))
            if member.unpaid_fines > 0:
                raise UserError(self.env._(
                    "%s has unpaid fines. Please settle them first.", member.name))
            if loan.copy_id.state != 'available':
                raise UserError(self.env._("This copy is not available."))
            loan.copy_id.state = 'borrowed'
            loan.state = 'borrowed'
        return True

    def action_return(self):
        for loan in self.filtered(lambda l: l.state in ('borrowed', 'overdue')):
            loan.return_date = fields.Date.context_today(self)
            if loan.copy_id.state == 'borrowed':
                loan.copy_id.state = 'available'
            loan.state = 'returned'
            if loan.fine_amount:
                loan.message_post(body=self.env._(
                    "Returned %(days)s day(s) late. Fine: %(fine)s",
                    days=loan.days_late, fine=loan.currency_id.format(loan.fine_amount)))
        return True

    def action_renew(self):
        today = fields.Date.context_today(self)
        for loan in self.filtered(lambda l: l.state in ('borrowed', 'overdue')):
            if loan.due_date < today:
                raise UserError(self.env._("Overdue loans cannot be renewed. Return the book first."))
            if loan.renew_count >= self._get_max_renewals():
                raise UserError(self.env._("Maximum number of renewals reached."))
            loan.due_date = loan.due_date + timedelta(days=self._get_loan_days())
            loan.renew_count += 1
        return True

    def action_mark_lost(self):
        for loan in self.filtered(lambda l: l.state in ('borrowed', 'overdue')):
            loan.copy_id.state = 'lost'
            loan.state = 'lost'
        return True

    def action_pay_fine(self):
        for loan in self:
            if not loan.fine_amount:
                raise UserError(self.env._("There is no fine to pay on this loan."))
            loan.fine_paid = True
        return True

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_update_overdue(self):
        today = fields.Date.context_today(self)
        open_late = self.search([
            ('state', 'in', ('borrowed', 'overdue')),
            ('due_date', '<', today),
        ])
        newly_overdue = open_late.filtered(lambda l: l.state == 'borrowed')
        newly_overdue.write({'state': 'overdue'})
        for loan in newly_overdue:
            loan.message_post(body=self.env._("This loan is now overdue."))
        open_late._compute_fine()  # refresh fine as days pass

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        """Return every figure shown on the Library Dashboard (JSON-safe)."""
        today = fields.Date.context_today(self)
        env = self.env
        currency = env.company.currency_id
        active_states = ('borrowed', 'overdue')

        unpaid = self._read_group(
            [('fine_amount', '>', 0), ('fine_paid', '=', False)], [], ['fine_amount:sum'])
        unpaid_fines = unpaid[0][0] if unpaid else 0.0

        first_of_month = today.replace(day=1)
        months = []
        for i in range(5, -1, -1):
            start = first_of_month - relativedelta(months=i)
            end = start + relativedelta(months=1)
            months.append({
                'label': start.strftime('%b'),
                'loans': self.search_count([
                    ('loan_date', '>=', start), ('loan_date', '<', end), ('state', '!=', 'draft')]),
                'returns': self.search_count([
                    ('return_date', '>=', start), ('return_date', '<', end)]),
            })

        top_books = [
            {'name': book.name, 'count': count}
            for book, count in self._read_group(
                [('state', '!=', 'draft')], ['book_id'], ['__count'],
                order='__count desc', limit=5)
        ]
        categories = [
            {'name': categ.name if categ else env._("Uncategorised"), 'count': count}
            for categ, count in self._read_group(
                [('state', '!=', 'draft')], ['category_id'], ['__count'],
                order='__count desc', limit=6)
        ]

        overdue = self.search([('state', '=', 'overdue')], order='due_date asc', limit=8)
        recent = self.search([('state', '!=', 'draft')], order='create_date desc, id desc', limit=6)

        def _row(loan):
            return {
                'id': loan.id,
                'name': loan.name,
                'member': loan.member_id.name,
                'book': loan.book_id.name,
                'due_date': fields.Date.to_string(loan.due_date),
                'days_late': loan.days_late,
                'fine': loan.fine_amount,
                'state': loan.state,
            }

        return {
            'today': fields.Date.to_string(today),
            'currency': {'symbol': currency.symbol, 'position': currency.position},
            'kpis': {
                'books': env['library.book'].search_count([]),
                'copies': env['library.book.copy'].search_count([]),
                'available': env['library.book.copy'].search_count([('state', '=', 'available')]),
                'members': env['library.member'].search_count([]),
                'active_loans': self.search_count([('state', 'in', active_states)]),
                'overdue': self.search_count([('state', '=', 'overdue')]),
                'due_today': self.search_count([('state', '=', 'borrowed'), ('due_date', '=', today)]),
                'unpaid_fines': unpaid_fines,
            },
            'months': months,
            'top_books': top_books,
            'categories': categories,
            'overdue_loans': [_row(l) for l in overdue],
            'recent_loans': [_row(l) for l in recent],
        }
