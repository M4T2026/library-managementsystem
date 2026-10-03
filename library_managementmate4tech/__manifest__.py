{
    'name': 'Library Management',
    'version': '19.0.1.0.0',
    'category': 'Services/Library',
    'summary': 'Complete library system: catalogue, barcoded copies, members, loans, fines and a live dashboard',
    'description': """
Library Management for Odoo 19
==============================
Run a school, university, company or community library inside Odoo.

* Live dashboard with KPIs, charts, overdue list and recent activity
* Catalogue of books, authors and categories with cover images
* Physical copies with automatic barcodes and status tracking
* Members with membership validity, loan limits and fine history
* Loans: borrow, renew, return, mark as lost
* Automatic overdue detection (daily scheduled action) and fine calculation
* Pivot / graph analysis, role based security, full chatter history
""",
    'author': 'Mate4Tech',
    'maintainer': 'Mate4Tech',
    'company': 'Mate4Tech',
    'website': 'https://mate4tech.com.au',
    'support': 'sales@mate4tech.com.au',
    'license': 'OPL-1',
    'price': 100.00,
    'currency': 'USD',
    'depends': ['base', 'mail'],
    'data': [
        'security/library_security.xml',
        'security/ir.model.access.csv',
        'data/library_data.xml',
        'views/book_views.xml',
        'views/member_views.xml',
        'views/loan_views.xml',
        'views/dashboard_views.xml',
        'views/library_menus.xml',
    ],
    'demo': ['demo/library_demo.xml'],
    'assets': {
        'web.assets_backend': [
            'library_management/static/src/scss/dashboard.scss',
            'library_management/static/src/js/dashboard.js',
            'library_management/static/src/xml/dashboard.xml',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/screenshots/01_dashboard.png',
        'static/description/screenshots/02_books_kanban.png',
        'static/description/screenshots/03_book_form.png',
        'static/description/screenshots/04_loans_list.png',
        'static/description/screenshots/05_loan_form.png',
        'static/description/screenshots/06_loan_analysis.png',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
