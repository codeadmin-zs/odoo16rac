from odoo import models, fields, api, exceptions
from datetime import datetime

from odoo.exceptions import UserError


class FleetVehicleExtend(models.Model):
    _inherit = 'fleet.vehicle'

    online_booking = fields.Boolean(string="Online booking", help="Allow renting of this product via online booking.",
                                    default=True)
    model_year = fields.Char(string="Model year",  size=4)
    # registration_number = fields.Char(string="Registration Number")
    registration_expiry = fields.Date('Registration Expiry')
    registration_cost = fields.Integer('Registration Cost')
    color_vehicle = fields.Char('Color of vehicle')
    next_service_date = fields.Date('Next Service Date')
    last_service_cost = fields.Float('Last service Cost')
    next_tyre_replacement_due = fields.Integer('Next Tyre Replacement')

    @api.constrains('model_year')
    def _check_year(self):
        for record in self:
            try:
                model_y = int(record.model_year)
                if model_y < 1900 or model_y > datetime.now().year + 1:
                    raise exceptions.ValidationError("Invalid year. Please enter a 4-digit year, ranging from 1900 to current year")
            except:
                raise exceptions.ValidationError("Invalid year. Please enter a 4-digit year, ranging from 1900 to current year.")

    @api.constrains('registration_expiry')
    def _check_registration_expiry(self):
        for record in self:
            reg_expiry_y = record.registration_expiry
            if reg_expiry_y < record.released_date:
                raise exceptions.ValidationError("Invalid Registration Expiry, Date Must be after to the Registration Date")

    def create(self, vals):
        if 'service_interval' in vals:
            try:
                service_interval = float(vals['service_interval'])
                if service_interval <= 0:
                    raise UserError("Service Due must be a positive number.")
            except ValueError:
                raise UserError("Service Due must be a valid number.")

        return super(FleetVehicleExtend, self).create(vals)

    def write(self, vals):
        if 'service_interval' in vals:
            try:
                service_interval = float(vals['service_interval'])
                if service_interval <= 0:
                    raise UserError("Service Due must be a positive number.")
            except ValueError:
                raise UserError("Service Due must be a valid number.")

        return super(FleetVehicleExtend, self).write(vals)