{
    'name': 'Fleet Rental Orders Sale',
    'version': '16.0.1.0.0',
    'author': 'Zaeem Solutions',
    'company': 'Zaeem Solutions',
    'website': "https://zaeemsolutions.com/",
    'depends': ['base', 'fleet', 'product', 'sale', 'fleet_rent'],
    'data': [
            # 'security/fleet_security.xml',
            'security/ir.model.access.csv',
            # 'data/fleet_prelocation.xml',
            'views/sale_products.xml',
            'views/rental_configurator_view.xml',
            'views/stock_move_line_lot_id_to_vin.xml',
    ],
    'demo': [
    ],
    "license": "LGPL-3",
    'installable': True,
    'application': True,
}