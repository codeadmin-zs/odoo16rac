{
    'name': 'VAT/TRN for UAE and OMAN',
    'version': '14.0.1.0.0',
    'depends': ['base', 'account', 'report_xlsx'],
    'data': [
                'security/ir.model.access.csv',
                'views/views.xml',
                'views/menu.xml',
                'views/reports.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}