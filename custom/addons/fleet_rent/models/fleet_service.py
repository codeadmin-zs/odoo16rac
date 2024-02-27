from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError, AccessError


class ServiceCategory(models.Model):
    _name = 'service.category'

    name = fields.Char(string="Service Category", size=2, translate=True)

    # @api.multi
    def copy(self, default=None):
        raise Warning(_('You can\'t duplicate record!'))

    # @api.multi
    def unlink(self):
        raise Warning(_('You can\'t delete record !'))


# class PendingRepairType(models.Model):
#     _name = 'pending.repair.type'
#
#     vehicle_rep_type_id = fields.Many2one('fleet.vehicle', string="Vehicle")
#     repair_type_id = fields.Many2one('repair.type', string="Repair Type")
#     name = fields.Char(string='Work Order ', translate=True)
#     categ_id = fields.Many2one("service.category", string="Category")
#     issue_date = fields.Date(string="Issue Date")
#     state = fields.Selection([('complete', 'Complete'),
#                               ('in-complete', 'Pending')], string="Status")
#     user_id = fields.Many2one('res.users', string="By")
#
#     # @api.multi
#     def copy(self, default=None):
#         raise Warning(_("You can\'t duplicate record !"))


class RepairType(models.Model):
    _name = 'repair.type'

    name = fields.Char(string='Repair Type', size=264,
                       translate=True)

    # @api.multi
    def copy(self, default=None):
        raise Warning(_('You can\'t duplicate record!'))

    # @api.multi
    def unlink(self):
        raise Warning(_('You can\'t delete record !'))


class WorkorderPartsHistoryDetails(models.Model):
    _name = 'workorder.parts.history.details'
    _order = 'used_date desc'

    team_id = fields.Many2one('fleet.team', string='Contract Trip')
    product_id = fields.Many2one('product.product', string='Part No',
                                 help='The Part Number')
    name = fields.Char(string='Part Name', help='The Part Name',
                       translate=True)
    vehicle_make = fields.Many2one('fleet.vehicle.model.brand',
                                   string='Vehicle Make',
                                   help='The Make of the Vehicle')
    used_qty = fields.Float(string='Encoded Qty',
                            help='The Quantity that is used in in Workorder')
    wo_encoded_qty = fields.Float(string='Qty',
                                  help='The Quantity which is \
                                  available to use')
    new_encode_qty = fields.Float(string='Qty for Encoding',
                                  help='New Encoded Qty')
    wo_id = fields.Many2one('fleet.vehicle.log.services', string='Workorder',
                            help='The workorder for which the part was used')
    used_date = fields.Datetime(string='Issued Date')
    issued_by = fields.Many2one('res.users', string='Issued by',
                                help='The user who would issue the parts')


class TripPartsHistoryDetailsTemp(models.Model):
    _name = 'trip.encoded.history.temp'

    team_id = fields.Many2one('fleet.team', string='Contract Trip')
    product_id = fields.Many2one('product.product', string='Part No',
                                 help='The Part Number')
    used_qty = fields.Float(string='Used Qty',
                            help='The Quantity that is used in in Workorder')
    work_order_id = fields.Many2one('fleet.vehicle.log.services',
                                    string="Work Order")

class NextServiceDays(models.Model):
    _name = 'next.service.days'

    def _default_vehicle_id_for_service_day(self):
        if self.env.context.get('default_vehicle_id', False):
            return self.env['fleet.vehicle'].browse(self.env.context.get('default_vehicle_id'))

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Id', default=_default_vehicle_id_for_service_day)
    name = fields.Char(string='Name', translate=True)
    # vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Id')
    days = fields.Integer(string='Days')

    # @api.multi
    def copy(self, default=None):
        raise Warning(_("You can\'t duplicate record !!"))


# Buffer Hours Model
class BufferHours(models.Model):
    _name = "buffer.hours"

    hours = fields.Float(
            string='Buffer Hours',
            digits=(10, 2),
            help='buffer hours',
            default=0.0,
        )
    @api.model
    def create(self, vals):
        existing_record = self.search([], limit=1)
        if existing_record:
            existing_record.write({'hours': vals.get('hours')})
            return existing_record
        return super(BufferHours, self).create(vals)

    # @api.multi
    def unlink(self):
        if len(self) == 1:
            raise UserError("You cannot delete the record ,Should retain at least one record")
        return super(BufferHours, self).unlink()
