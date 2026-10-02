# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date, timedelta


class LibraryDashboard(models.Model):
    _name = 'library.dashboard'
    _description = 'Library Dashboard'

    @api.model
    def get_dashboard_data(self):
        """Return all statistics for the dashboard."""
        today = date.today()
        month_start = today.replace(day=1)

        Book = self.env['library.book']
        Member = self.env['library.member']
        Borrowing = self.env['library.borrowing']
        Reservation = self.env['library.reservation']

        # Book stats
        total_books = Book.search_count([])
        available_books = Book.search_count([('state', '=', 'available')])
        borrowed_books = Book.search_count([('state', '=', 'borrowed')])

        # Member stats
        total_members = Member.search_count([])
        active_members = Member.search_count([('state', '=', 'active')])
        expired_members = Member.search_count([('state', '=', 'expired')])

        # Borrowing stats
        total_borrowings = Borrowing.search_count([])
        active_borrowings = Borrowing.search_count([('state', 'in', ['borrowed', 'overdue'])])
        overdue_borrowings = Borrowing.search_count([('state', '=', 'overdue')])
        returned_today = Borrowing.search_count([
            ('return_date', '=', today),
            ('state', '=', 'returned'),
        ])
        borrowed_this_month = Borrowing.search_count([
            ('borrow_date', '>=', month_start),
        ])

        # Fine stats
        total_fines = sum(
            Borrowing.search([('fine_amount', '>', 0), ('fine_paid', '=', False)]).mapped('fine_amount')
        )

        # Reservations
        active_reservations = Reservation.search_count([('state', '=', 'reserved')])

        # Top borrowed books (last 30 days)
        thirty_days_ago = today - timedelta(days=30)
        recent_borrowings = Borrowing.search([('borrow_date', '>=', thirty_days_ago)])
        book_borrow_counts = {}
        for b in recent_borrowings:
            book_borrow_counts[b.book_id.id] = book_borrow_counts.get(b.book_id.id, 0) + 1
        top_books = sorted(book_borrow_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_books_data = []
        for book_id, count in top_books:
            book = Book.browse(book_id)
            top_books_data.append({'name': book.name, 'count': count})

        # Monthly borrowing trend (last 6 months)
        monthly_trend = []
        for i in range(5, -1, -1):
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            m_start = month_date.replace(day=1)
            if month_date.month == 12:
                m_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                m_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
            count = Borrowing.search_count([
                ('borrow_date', '>=', m_start),
                ('borrow_date', '<=', m_end),
            ])
            monthly_trend.append({
                'month': m_start.strftime('%b %Y'),
                'count': count,
            })

        # Category distribution
        categories = self.env['library.category'].search([])
        category_data = []
        for cat in categories:
            count = Book.search_count([('category_id', 'child_of', cat.id)])
            if count > 0:
                category_data.append({'name': cat.name, 'count': count})

        return {
            'total_books': total_books,
            'available_books': available_books,
            'borrowed_books': borrowed_books,
            'total_members': total_members,
            'active_members': active_members,
            'expired_members': expired_members,
            'total_borrowings': total_borrowings,
            'active_borrowings': active_borrowings,
            'overdue_borrowings': overdue_borrowings,
            'returned_today': returned_today,
            'borrowed_this_month': borrowed_this_month,
            'total_fines': total_fines,
            'active_reservations': active_reservations,
            'top_books': top_books_data,
            'monthly_trend': monthly_trend,
            'category_data': category_data,
        }
