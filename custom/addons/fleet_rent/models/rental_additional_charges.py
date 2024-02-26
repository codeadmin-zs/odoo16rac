from odoo import models, fields, _, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
import time


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    def _default_current_odometer(self):
        if self.vehicle_id:
            current_odometer = self.vehicle_id.odometer
            return current_odometer

    def _set_odometer(self):
        fleet_odometer_obj = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = fleet_odometer_obj.search(
                [('vehicle_id', '=', record.vehicle_id.id)],
                limit=1, order='value desc')
            if record.current_odometer < vehicle_odometer.value:
                raise Warning(('User Error!\nYou can\'t enter odometer less \
                than previous odometer %s !') % (vehicle_odometer.value))
            if record.current_odometer:
                date = fields.Date.context_today(record)
                data = {'value': record.current_odometer, 'date': date,
                        'vehicle_id': record.vehicle_id.id}
                fleet_odometer_obj.create(data)

    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehicle',
        help="Name of Vehicle.")
    vehicle_id_temp = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehicle',
        help="Name of Vehicle.")
    name = fields.Char(string='Analytic Account', index=True, required=True, tracking=True, store=True)
    ten_date = fields.Datetime(
        string='Date',
        default=lambda *a: time.strftime(DT),
        help="Rental Vehicle contract creation date.")
    current_odometer = fields.Float(default=_default_current_odometer, inverse='_set_odometer',
                                    required=True, string=' Current Odometer',
                                    help='Odometer measure of the vehicle at the moment of this log')
    current_odometer_temp = fields.Float(default=_default_current_odometer,
                                    required=True, string=' Current Odometer',
                                    help='Odometer measure of the vehicle at the moment of this log')
    closing_odometer = fields.Float(string='Closing Odometer', inverse='_set_odometer',
                                    help='Odometer measure of the vehicle at the moment of this log')
    closing_odometer_temp = fields.Float(string='Closing Odometer', inverse='_set_odometer',
                                    help='Odometer measure of the vehicle at the moment of this log')
    duration = fields.Integer(string="Duration", default=1, required=True,
                              help="Duration of the rental (in unit of the pricing)")
    duration_unit = fields.Selection([("hour", "Hours"), ("day", "Days"), ("week", "Weeks"), ("month", "Months")],
                                     string="Unit", required=True, default="day")
    invoice_policies = fields.Selection(
        [("advanced", "Advance Invoicing"), ("periodic", "Periodic Invoicing"), ("post_invoicing", "Post Invoicing"), ],
        string="Invoicing Policy", required=True, default="advanced")
    lock_state = fields.Selection(
        [('locked', 'Locked'),
         ('open', 'Not Locked')],
        string='Locked Order',
        required=True,
        copy=False,
        default='open', track_visibility='onchange')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    vehicle_return_attachment = fields.Binary(
        string='Return Document',
        help='Vehicle Return document attachment for selected vehicle')
    tenant_id = fields.Many2one('res.partner', string='Tenant', help="Tenant Name of Rental Vehicle.")
    manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Account Manager', default=lambda self: self.env.user,
        help="Manager of Rental Vehicle.")
    rent = fields.Float(string='Rental Vehicle Rent', default=0.0, currency_field='currency_id',
                        help="Rental vehicle rent for selected vehicle per rent type.")
    vehicle_lot_id = fields.Many2one('stock.lot', string='Lot ID')
    product_id = fields.Many2one('product.product', string='Product Variant ID')

    fuel_level_temp = fields.Selection([('0', 'Empty'),
                                        ('1', '1/8'),
                                        ('2', '2/8'),
                                        ('3', '3/8'),
                                        ('4', '4/8'),
                                        ('5', '5/8'),
                                        ('6', '6/8'),
                                        ('7', '7/8'),
                                        ('8', 'Full')],
                                       string='Fuel Level', readonly=False, store=True)