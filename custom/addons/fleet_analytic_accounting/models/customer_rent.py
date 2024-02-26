from odoo import fields, models

class RentalDetails(models.Model):
    _inherit = "res.partner"

    rent_details = fields.One2many("account.analytic.account", 'tenant_id')
