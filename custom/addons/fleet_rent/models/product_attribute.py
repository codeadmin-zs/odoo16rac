from odoo import models, fields, api


class ProductAttribute(models.Model):
    _inherit = "product.attribute.value"

    vehicle_model_id = fields.Many2one('fleet.vehicle.model', string='Vehicle Model')
