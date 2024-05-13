{
    'name': 'Master Table Demo Data',
    'version': '16.0.1.0.0',
    'author': 'Zaeem Solutions',
    'company': 'Zaeem Solutions',
    'website': "https://zaeemsolutions.com/",
    'depends': ['base','account','purchase','sale_management','stock',
                'base_accounting_kit','fleet','fleet_rental','asset_loan',
                'fleet_rent','fleet_analytic_accounting','rental_orders_sale'],
    'data': [
            'data/users_demo.xml',
            'data/vehicle_class.xml',
            'data/product.xml',
            'data/product_vehicle_category.xml',
            'data/oman_states.xml',
    ],
    'demo': [
    ],
    "license": "LGPL-3",
    'installable': True,
    'application': True,
}