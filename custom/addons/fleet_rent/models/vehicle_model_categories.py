from odoo import fields, models

class VehicleCategory(models.Model):
    _name = 'vehicle.category'

    name = fields.Char('Vehicle Category')
