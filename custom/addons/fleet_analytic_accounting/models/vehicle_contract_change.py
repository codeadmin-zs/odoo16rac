from odoo import models, fields, api


class VehicleContractChange(models.Model):
    _name = 'vehicle.contract.change'

    active_contract_id = fields.Many2one('account.analytic.account',string="Contract ID")
    reason = fields.Char(String='Reason')
    date = fields.Datetime(String='Extend Date')
    duration = fields.Integer(string='Duration')
    duration_unit = fields.Selection([("hour", "Hourly"), ("day", "Daily"), ("week", "Weekly"), ("month", "Monthly")],
                                     string="Unit", required=True, default="day")


class VehicleContractLog(models.Model):
    _name = 'vehicle.contract.log'

    contract_id = fields.Many2one('account.analytic.account')
    cont_vehicle = fields.Many2one('fleet.vehicle', string='Vehicle')
    cont_start_date = fields.Datetime(string='Start Date')
    cont_end_date = fields.Datetime(string='End Date')
    cont_current_odometer = fields.Float(string='Starting Odometer')
    cont_closing_odometer = fields.Float(string='Closing Odometer')


