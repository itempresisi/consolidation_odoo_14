# -*- coding: utf-8 -*-
{
    'name': 'Financial Consolidation',
    'version': '14.0.1.0.0',
    'category': 'Accounting/Consolidation',
    'summary': 'Multi-company financial statements consolidation',
    'description': """
Financial Consolidation
======================
This module allows for the consolidation of financial statements across multiple companies with:
- Proper elimination entries
- Currency conversion
- Consolidated reporting
- Multi-company support
- Different consolidation methods (full, proportional, equity)
- Intercompany transaction elimination
- Financial statement generation
    """,
    'author': 'Claude',
    'website': 'https://www.example.com',
    'depends': ['account', 'base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/consolidation_data.xml',
        'data/account_data.xml',
        'views/consolidation_group_views.xml',
        'views/consolidation_period_views.xml',
        'views/consolidation_account_views.xml',
        'views/consolidation_journal_views.xml',
        'views/intercompany_views.xml',
        'views/analysis_views.xml',
        'views/res_company_views.xml',
        'views/menu_views.xml',
        'report/consolidation_report.xml',
        'wizards/consolidation_wizard_views.xml',
        'wizards/intercompany_matching_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}