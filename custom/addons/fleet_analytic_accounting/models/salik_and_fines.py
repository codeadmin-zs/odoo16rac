from odoo import models, fields, api
from datetime import datetime


class FleetVehicleSalikCharges(models.Model):
    _name = 'vehicle.salik.charge'

    salik_product_id = fields.Many2one('product.product', string='Product',
                                       required=True,
                                       domain=[('product_tmpl_id.accessories_ok', '=', True)])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Partner')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    plate_no = fields.Char(string='Vehicle Number', related='analytic_account_id.vehicle_id.license_plate')
    unit_price = fields.Float('Unit Price', readonly=False)
    location = fields.Char(string='Location', required=True)
    description = fields.Text(string='Description')
    time_date = fields.Datetime('Toll Date', required=True, default=lambda s: datetime.now())
    contract_details = fields.Many2one('fleet.rental.vehicle.details', string='Rental Vehicle Details')

    @api.onchange('salik_product_id')
    def onchange_vehicle_fine(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        new_product = self.env.ref('fleet_rent.additional_charge_toll_charges').product_variant_id
        self.salik_product_id = new_product.id
        self.vehicle_id = tenancy_id.vehicle_id
        self.plate_no = tenancy_id.vehicle_id.license_plate
        self.analytic_account_id = tenancy_id.rental_contract_id


class FleetVehicleFineCharges(models.Model):
    _name = 'vehicle.fine.charge'

    fine_product_id = fields.Many2one('product.product', string='Product',
                                      required=True,
                                      domain=[('product_tmpl_id.accessories_ok', '=', True)])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Partner')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    plate_no = fields.Char(string='Vehicle Number', related='vehicle_id.license_plate')
    unit_price = fields.Float('Unit Price', readonly=False)
    location = fields.Char(string='Location', required=True)
    description = fields.Text(string='Description')
    time_date = fields.Datetime('Fine Date', required=True, default=lambda s: datetime.now())
    contract_details = fields.Many2one('fleet.rental.vehicle.details', string='Rental Vehicle Details')

    @api.onchange('fine_product_id')
    def onchange_vehicle_fine(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        new_product = self.env.ref('fleet_rent.additional_charge_fines').product_variant_id
        self.fine_product_id = new_product.id
        self.vehicle_id = tenancy_id.vehicle_id
        self.plate_no = tenancy_id.vehicle_id.license_plate
        self.analytic_account_id = tenancy_id.rental_contract_id
