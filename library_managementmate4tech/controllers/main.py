# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class LibraryController(http.Controller):

    @http.route('/library/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):
        """JSON endpoint for dashboard data."""
        data = request.env['library.dashboard'].get_dashboard_data()
        return data

    @http.route('/library/book/search', type='json', auth='user')
    def search_books(self, query='', limit=10):
        """Quick book search endpoint."""
        books = request.env['library.book'].search([
            '|',
            ('name', 'ilike', query),
            ('isbn', 'ilike', query),
        ], limit=limit)
        return [{
            'id': b.id,
            'name': b.name,
            'isbn': b.isbn,
            'available': b.available_copies,
            'status': b.state,
        } for b in books]
