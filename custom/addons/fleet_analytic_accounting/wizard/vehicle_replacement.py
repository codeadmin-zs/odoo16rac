from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class WizardRentReplace(models.TransientModel):
    _name = 'rent.vehicle.replace'

    # set domain for new vehicle to filter the vehicles with rent in the selected period
    @api.onchange('current_vehicle_id')
    def set_domain_for_new_vehicle(self):
        anlytic_obj = self.env['account.analytic.account']
        avilable_records = anlytic_obj.search(['|', ('state', '!=', 'close'), '|',
                                               ('date_start', '>=', self.date_start),
                                               ('date_start', '>=', self.date), '|',
                                               ('date', '>=', self.date_start),
                                               ('date', '>=', self.date),
                                               ('id', '!=', self._context.get('active_id'))])
        msg1 = ("This is my debug message avilable_records')! %s", avilable_records)
        _logger.error(msg1)
        vehicle_list = []
        if avilable_records:
            for record in avilable_records:
                if record.date_start and record.date and record.vehicle_id:
                    # msg1 = ("This is my debug message check! ")
                    # _logger.error(msg1)
                    cond1 = (self.date_start <= record.date_start <= self.date)
                    # msg1 = ("This is my debug message self.date_start <= record.date_start <= self.date')! %s %s %s",self.date_start , record.date_start , self.date)
                    # _logger.error(msg1)
                    cond2 = (self.date_start <= record.date <= self.date)
                    if (cond1 or cond2) and record.vehicle_id != self.current_vehicle_id:
                        vehicle_list.append(record.vehicle_id.id)
        fleet_obj = self.env['fleet.vehicle'].search([('state_id', '=', 7)])
        for ids in fleet_obj:
            vehicle_list.append(ids.id)
        res = {}
        vehicle_list.append(self.current_vehicle_id.id)
        res['domain'] = {'new_vehicle_id': [('id', 'not in', vehicle_list)]}
        msg1 = ("This is my debug message res')! %s", res)
        _logger.error(msg1)
        return res

    def _default_date(self):
        if self.env.context.get('default_date', False):
            return self.env.context.get('default_date')

    def _default_start_date(self):
        if self.env.context.get('default_start_date', False):
            return self.env.context.get('default_start_date')

    def _default_current_vehicle_id(self):
        if self.env.context.get('default_vehicle_id', False):
            return self.env.context.get('default_vehicle_id')

    current_vehicle_id = fields.Many2one('fleet.vehicle', default=_default_current_vehicle_id,
                                         string='Current Vehicle ID')
    new_vehicle_id = fields.Many2one('fleet.vehicle', string='Replacement Vehicle')
    date = fields.Datetime(string='Expiration Date', default=_default_date, help="Rental Vehicle contract end date.")
    date_start = fields.Datetime(string='Start Date', default=_default_start_date,
                                 help="Rental Vehicle contract start date .")
    reason = fields.Selection(
        [('accident', 'Accident'),
         ('replacement', 'Replacement')],
        string='Reason', required=True, copy=False, default='replacement')

    # @api.multi
    def replace_vehicle(self):
        if self._context.get('active_id', False) and self._context.get('active_model', False):
            for reason in self.env[self._context['active_model']].browse(self._context.get('active_id', False)):
                reason.write({'vehicle_id': self.new_vehicle_id.id})
                fleet_vehicle_state = self.env['fleet.vehicle.state'].search([('name', '=', 'Replaced')])
                self.current_vehicle_id.update({'state': self.reason, 'state_id': fleet_vehicle_state.id})
                self.new_vehicle_id.update({'state': 'rent', 'state_id': 9})
        return True

    # @api.model
    # def create(self, vals):
    #     """
    #     This Method is used to overrides orm create method,
    #     to change state and tenant of related property.
    #     @param self: The object pointer
    #     @param vals: dictionary of fields value.
    #     """
    #     vehicle_id = vals.get('vehicle_id', False)
    #     st_dt = vals.get('date_start', False)
    #     vehicle_obj = self.env['fleet.vehicle']
    #     veh_ser_obj = self.env['fleet.vehicle.log.services']
    #     vehicle_rec = vehicle_obj.browse(vehicle_id)
    #     veh_ser_rec = veh_ser_obj.search([('vehicle_id', '=', vehicle_id),
    #                                       ('date_complete', '>', st_dt)])
    #     if vehicle_rec.state == 'in_progress' and veh_ser_rec:
    #         raise ValidationError('This Vehicle In Service. So You Can Not\
    #                                     Create Rent Order For This Vehicle.')
    #     if not vals:
    #         vals = {}
    #     if 'tenant_id' in vals:
    #         vals['ref'] = self.env['ir.sequence'].next_by_code(
    #             'account.analytic.account')
    #         vals.update({'is_property': True})
    #     res = super(AccountAnalyticAccount, self).create(vals)
    #
    #     for rent_rec in self:
    #         msg1 = ("This is my debug message vals.get('state')! %s",vals)
    #         _logger.error(msg1)
    #         if vals.get('state'):
    #             if vals['state'] == 'draft':
    #                 rent_rec.vehicle_id.write({'state': 'booked'})
    #     st_dt = res.date_start
    #     en_dt = res.date
    #     veh_id = res.vehicle_id and res.vehicle_id.id or False
    #     anlytic_obj = self.env['account.analytic.account']
    #     avilable_records = anlytic_obj.search([('state', '!=', 'close'),
    #                                            ('vehicle_id', '=', veh_id),
    #                                            ('id', '!=', res.id)])
    #     if avilable_records:
    #         for rec in avilable_records:
    #             if rec.date_start and rec.date:
    #                 cond1 = (st_dt < rec.date_start < en_dt)
    #                 cond2 = (st_dt < rec.date < en_dt)
    #                 if cond1 or cond2:
    #                     raise ValidationError('This vehicle is already on rent. You can not create another rent for this vehicle on same rent date.')
