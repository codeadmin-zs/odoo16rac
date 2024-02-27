from odoo import fields, models, api
from odoo.exceptions import ValidationError


class NewVehicleDetails(models.Model):
    _inherit = 'product.template'

    name = fields.Char('Name', index=True, translate=True, trackvisibility='onchange')
    model_id_temp = fields.Many2one("Vehicle Model", 'fleet.vehicle.model')
    model_name = fields.Char('Name', required=1)
    brand_id_temp = fields.Many2one('fleet.vehicle.model.brand', 'Manufacturer', required=True,
                                   help='Manufacturer of the vehicle')
    vehicle_type = fields.Selection([('car', 'Car'), ('bike', 'Bike')], default='car', required=True)
    # manager_id = fields.Many2one('res.users', compute='_compute_manager_id', domain=lambda self: [
    #     ('groups_id', 'in', self.env.ref('fleet.fleet_group_manager').id)], store=True, readonly=False)
    category_vehicle_fuel_id = fields.Many2one('fleet.category.vehicle.fuel', string='Fuel', required=True)
    fuel_tank_capacity = fields.Integer(string='Fuel Tank Capacity', required=True, default=55)
    category_vehicle_class_id = fields.Many2one('vehicle.category', string='Vehicle Category', required=True)
    category_vehicle_transmission_id = fields.Many2one('fleet.category.vehicle.transmission', string='Transmission',
                                                       required=True)
    doors = fields.Integer('Doors Number', help='Number of doors of the vehicle', default=4)
    seats = fields.Integer('Seats Number', help='Number of seats of the vehicle', default=5)

    @api.onchange('model_name', 'brand_id_temp')
    def set_product_name(self):
        if self.model_name and self.brand_id_temp:
            self.name = self.brand_id_temp.name + ' ' + self.model_name


    def write(self, vals):
        res = super(NewVehicleDetails, self).write(vals)
        if self.qty_available > 0:
            if self.accessories_ok:
                raise ValidationError('Cannot change to Accessories')
        return res
