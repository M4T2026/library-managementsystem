# -*- coding: utf-8 -*-
{
    'name': 'Library Management System',
    'version': '19.0.1.0.0',
    'category': 'Industries',
    'summary': 'Complete Library Management System with Book Borrowing, Member Management, Dashboard & Reports',
    'description': """
        Complete Library Management System for Odoo 19
        ================================================
        Manage your library efficiently with this comprehensive module.

        Features:
        ---------
        * Book & Author Management
        * Member Management with Library Cards
        * Book Borrowing & Return Workflow
        * Overdue Tracking & Fine Calculation
        * Beautiful Dashboard with Statistics
        * Email Notifications
        * Reports: Borrowing, Overdue, Member Card
        * Category & Publisher Management
        * Book Reservation System
        * Barcode Support
    """,
    'author': 'mate4tech',
    'company': 'mate4tech',
    'website': 'https://www.mate4tech.com.au',
    'email': 'sales@mate4tech.com.au',
    'license': 'OPL-1',
    'support': 'sales@mate4tech.com.au',
    'maintainer': 'mate4tech',
    'images': ['static/description/banner.png'],
    'depends': [
        'base',
        'mail',
        'portal',
        'account',
        'product',
        'web',
    ],
    'data': [
        # Security
        'security/library_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/library_sequence.xml',
        'data/library_data.xml',
        'data/email_template.xml',
        'data/automated_actions.xml',

        # Views
        'views/library_category_views.xml',
        'views/library_publisher_views.xml',
        'views/library_author_views.xml',
        'views/library_book_views.xml',
        'views/library_member_views.xml',
        'views/library_borrowing_views.xml',
        'views/library_reservation_views.xml',
        'views/library_fine_views.xml',
        'views/library_dashboard_views.xml',

        # Wizards
        'wizards/borrow_book_wizard_views.xml',
        'wizards/return_book_wizard_views.xml',
        'wizards/renew_borrowing_wizard_views.xml',

        # Reports
        'reports/borrowing_report.xml',
        'reports/overdue_report.xml',
        'reports/member_card_report.xml',
        'reports/library_report_templates.xml',

        # Menus
        'views/library_menu_views.xml',
    ],
    'demo': [
        'demo/library_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'library_management/static/src/css/library_dashboard.css',
            'library_management/static/src/js/library_dashboard.js',
            'library_management/static/src/js/library_dashboard_template.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 49.99,
    'currency': 'USD',
}
