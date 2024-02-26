from odoo import models, fields
from datetime import datetime

from dateutil.relativedelta import relativedelta


class WizardHandOverChecking(models.TransientModel):
    _name = 'vehicle.handover'

    def _default_vehicle_id_handover(self):
        if self.env.context.get('default_vehicle_id', False):
            return self.env['fleet.vehicle'].browse(self.context.get('default_vehicle_id'))

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', help="Name of Vehicle.",
                                 track_visibility='onchange', default=_default_vehicle_id_handover)
    # fuel level
    fuel_level = fields.Selection([('0', 'Empty'),
                                   ('8', 'Full'),
                                   ('1', '1/8'),
                                   ('2', '2/8'),
                                   ('3', '3/8'),
                                   ('4', '4/8'),
                                   ('5', '5/8'),
                                   ('5', '6/8'),
                                   ('7', '7/8')],
                                  string='Fuel Level', readonly=False,
                                  related='vehicle_id.fuel_level', required=True)
    # dents
    hood_dent = fields.Boolean(string="Hood", related='vehicle_id.hood_dent', default=True)
    front_r_door_dent = fields.Boolean(string="Front Door (R)", related='vehicle_id.front_r_door_dent', default=True)
    front_l_door_dent = fields.Boolean(string="Front Door (L)", related='vehicle_id.front_l_door_dent', default=True)
    back_r_door_dent = fields.Boolean(string="Back Door (R)", related='vehicle_id.back_r_door_dent', default=True)
    back_l_door_dent = fields.Boolean(string="Back Door (L)", related='vehicle_id.back_l_door_dent', default=True)
    boot_dent = fields.Boolean(string="Boot", related='vehicle_id.boot_dent', default=True)
    # dent count
    hood_dent_count = fields.Integer(string="Hood", related='vehicle_id.hood_dent_count')
    front_r_door_dent_count = fields.Integer(string="Front Door (R)", related='vehicle_id.front_r_door_dent_count')
    front_l_door_dent_count = fields.Integer(string="Front Door (L)", related='vehicle_id.front_l_door_dent_count')
    back_r_door_dent_count = fields.Integer(string="Back Door (R)", related='vehicle_id.back_r_door_dent_count')
    back_l_door_dent_count = fields.Integer(string="Back Door (L)", related='vehicle_id.back_l_door_dent_count')
    boot_dent_count = fields.Integer(string="Boot", related='vehicle_id.boot_dent_count')

    hood_dent_count_new = fields.Integer(string="Hood")
    front_r_door_dent_count_new = fields.Integer(string="Front Door (R)")
    front_l_door_dent_count_new = fields.Integer(string="Front Door (L)")
    back_r_door_dent_count_new = fields.Integer(string="Back Door (R)")
    back_l_door_dent_count_new = fields.Integer(string="Back Door (L)")
    boot_dent_count_new = fields.Integer(string="Boot")

    # scratches
    hood_scratch = fields.Boolean(string="Hood", related='vehicle_id.hood_scratch', default=True)
    front_r_door_scratch = fields.Boolean(string="Front Door (R)", related='vehicle_id.front_r_door_scratch', default=True)
    front_l_door_scratch = fields.Boolean(string="Front Door (L)", related='vehicle_id.front_l_door_scratch', default=True)
    back_r_door_scratch = fields.Boolean(string="Back Door (R)", related='vehicle_id.back_r_door_scratch', default=True)
    back_l_door_scratch = fields.Boolean(string="Back Door (L)", related='vehicle_id.back_l_door_scratch', default=True)
    boot_scratch = fields.Boolean(string="Boot", related='vehicle_id.boot_scratch', default=True)
    # scratch count
    hood_scratch_count = fields.Integer(string="Hood", related='vehicle_id.hood_scratch_count')
    front_r_door_scratch_count = fields.Integer(string="Front Door (R)", related='vehicle_id.front_r_door_scratch_count')
    front_l_door_scratch_count = fields.Integer(string="Front Door (L)", related='vehicle_id.front_l_door_scratch_count')
    back_r_door_scratch_count = fields.Integer(string="Back Door (R)", related='vehicle_id.back_r_door_scratch_count')
    back_l_door_scratch_count = fields.Integer(string="Back Door (L)", related='vehicle_id.back_l_door_scratch_count')
    boot_scratch_count = fields.Integer(string="Boot", related='vehicle_id.boot_scratch_count')

    hood_scratch_count_new = fields.Integer(string="Hood")
    front_r_door_scratch_count_new = fields.Integer(string="Front Door (R)")
    front_l_door_scratch_count_new = fields.Integer(string="Front Door (L)")
    back_r_door_scratch_count_new = fields.Integer(string="Back Door (R)")
    back_l_door_scratch_count_new = fields.Integer(string="Back Door (L)")
    boot_scratch_count_new = fields.Integer(string="Boot")

    current_odometer = fields.Float(string='Current Odometer', related='vehicle_id.odometer', readonly=False,
                                    help='Odometer measure of the vehicle at handover', required="1")

    handover_date = fields.Datetime('Handover Date', help="Date of Vehicle Handover",
                                    required=True, default=lambda s: datetime.now() + relativedelta(minute=0, second=0, hours=1))

    def confirm_handover(self):
        if self._context.get('active_id', False) and self._context.get('active_model', False):
            for reason in self.env[self._context['active_model']].browse(self._context.get('active_id', False)):
                reason.write({'state': 'open',
                              'current_odometer': self.current_odometer,
                              'date_start': self.handover_date})
        if self.vehicle_id:
            self.vehicle_id.update({'hood_dent': self.hood_dent,
                                    'front_r_door_dent': self.front_r_door_dent,
                                    'front_l_door_dent': self.front_l_door_dent,
                                    'back_r_door_dent': self.back_r_door_dent,
                                    'back_l_door_dent': self.back_l_door_dent,
                                    'boot_dent': self.boot_dent,
                                    'hood_scratch': self.hood_scratch,
                                    'front_r_door_scratch': self.front_r_door_scratch,
                                    'front_l_door_scratch': self.front_l_door_scratch,
                                    'back_r_door_scratch': self.back_r_door_scratch,
                                    'back_l_door_scratch': self.back_l_door_scratch,
                                    'boot_scratch': self.boot_scratch,
                                    'hood_dent_count': self.hood_dent_count + self.hood_dent_count_new,
                                    'front_r_door_dent_count': self.front_r_door_dent_count + self.front_r_door_dent_count_new,
                                    'front_l_door_dent_count': self.front_l_door_dent_count + self.front_l_door_dent_count_new,
                                    'back_r_door_dent_count': self.back_r_door_dent_count + self.back_r_door_dent_count_new,
                                    'back_l_door_dent_count': self.back_l_door_dent_count + self.back_l_door_dent_count_new,
                                    'boot_dent_count': self.boot_dent_count + self.boot_dent_count_new,
                                    'hood_scratch_count': self.hood_scratch_count + self.hood_scratch_count_new,
                                    'front_r_door_scratch_count': self.front_r_door_scratch_count + self.front_r_door_scratch_count_new,
                                    'front_l_door_scratch_count': self.front_l_door_scratch_count + self.front_l_door_scratch_count_new,
                                    'back_r_door_scratch_count': self.back_r_door_scratch_count + self.back_r_door_scratch_count_new,
                                    'back_l_door_scratch_count': self.back_l_door_scratch_count + self.back_l_door_scratch_count_new,
                                    'boot_scratch_count': self.boot_scratch_count + self.boot_scratch_count_new,
                                    'state': 'rent',
                                    'state_id': 9,
                                    'odometer': self.current_odometer,
                                    'active_contract': self.rental_contract_id})
        return True
