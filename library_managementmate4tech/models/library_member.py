from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(related='partner_id.name', store=True)
    partner_id = fields.Many2one(
        'res.partner', string='Contact', required=True, ondelete='restrict', tracking=True)
    member_number = fields.Char(readonly=True, copy=False, default='New', index=True)
    join_date = fields.Date(default=fields.Date.context_today)
    expiry_date = fields.Date(
        string='Membership Expiry', required=True, tracking=True,
        default=lambda self: fields.Date.context_today(self) + relativedelta(years=1))
    max_loans = fields.Integer(string='Max Simultaneous Loans', default=5)
    is_expired = fields.Boolean(compute='_compute_is_expired')
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id)

    loan_ids = fields.One2many('library.loan', 'member_id', string='Loans')
    loan_count = fields.Integer(compute='_compute_loan_stats')
    active_loan_count = fields.Integer(compute='_compute_loan_stats')
    unpaid_fines = fields.Monetary(compute='_compute_loan_stats', currency_field='currency_id')

    _partner_uniq = models.Constraint('UNIQUE(partner_id)', 'This contact is already a member.')

    @api.constrains('join_date', 'expiry_date')
    def _check_dates(self):
        for member in self:
            if member.join_date and member.expiry_date and member.expiry_date < member.join_date:
                raise ValidationError(self.env._("Expiry date cannot be before the join date."))

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for member in self:
            member.is_expired = bool(member.expiry_date and member.expiry_date < today)

    @api.depends('loan_ids.state', 'loan_ids.fine_amount', 'loan_ids.fine_paid')
    def _compute_loan_stats(self):
        for member in self:
            loans = member.loan_ids
            member.loan_count = len(loans)
            member.active_loan_count = len(loans.filtered(lambda l: l.state in ('borrowed', 'overdue')))
            member.unpaid_fines = sum(loans.filtered(lambda l: not l.fine_paid).mapped('fine_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('member_number', 'New') == 'New':
                vals['member_number'] = self.env['ir.sequence'].next_by_code('library.member') or 'New'
        return super().create(vals_list)

    def action_renew_membership(self):
        today = fields.Date.context_today(self)
        for member in self:
            member.expiry_date = max(member.expiry_date or today, today) + relativedelta(years=1)

    def action_view_loans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'library.loan',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }
