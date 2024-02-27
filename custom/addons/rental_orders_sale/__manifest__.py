{
    'name': 'Fleet Rental Orders Sale',
    'version': '14.0.1.0.0',
    'depends': ['base', 'fleet', 'product', 'sale', 'fleet_rent'],
    'data': [
            # 'security/fleet_security.xml',
            'security/ir.model.access.csv',
            # 'data/fleet_prelocation.xml',
            # 'wizard/update_history_view.xml',
            'views/sale_products.xml',
            'views/rental_configurator_view.xml',
            'views/stock_move_line_lot_id_to_vin.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}