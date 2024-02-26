from odoo import models, fields


class FleetVehicle(models.Model):
    """This is the Fleet vehicle model."""
    _inherit = 'fleet.vehicle'

    def _compute_count_all(self):
        Odometer = self.env['fleet.vehicle.odometer']
        LogService = self.env['fleet.vehicle.log.services']
        LogContract = self.env['fleet.vehicle.log.contract']
        service_type_id = self.env.ref('account_fleet.data_fleet_service_type_vendor_bill')
        for record in self:
            record.odometer_count = Odometer.search_count([('vehicle_id', '=', record.id)])
            record.service_count = LogService.search_count(
                [('vehicle_id', '=', record.id), ('service_type_id', '!=', service_type_id.id)])
            record.contract_count = LogContract.search_count(
                [('vehicle_id', '=', record.id), ('state', '!=', 'closed')])
            record.history_count = self.env['fleet.vehicle.assignation.log'].search_count(
                [('vehicle_id', '=', record.id)])

    service_count = fields.Integer(compute="_compute_count_all", string='Services')

    def return_action_to_create_contract(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        # context = dict(self._context or {})
        wiz_form_id = self.env.ref('fleet_analytic_accounting.property_analytic_view_form').id

        context = {'default_vehicle_id': self.id, 'default_vehicle_id_temp': self.id,
                   'default_current_odometer_temp': self.odometer, 'default_current_odometer': self.odometer}
        return {
            'name': 'Rental Contract',
            'res_model': 'account.analytic.account',
            'type': 'ir.actions.act_window',
            'context': context,
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current'
        }

    def return_action_to_list_contracts(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id('fleet_analytic_accounting.%s' % xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False

    def return_action_to_open_active_contract(self):
        self.ensure_one()
        wiz_form_id = self.env.ref('fleet_analytic_accounting.property_analytic_view_form').id

        context = {'default_vehicle_id': self.id}
        return {
            'name': 'Rental Contract',
            'res_model': 'account.analytic.account',
            'type': 'ir.actions.act_window',
            'context': context,
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'res_id': self.active_contract.id
        }

    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id('fleet.%s' % xml_id)
            domain = ''
            if xml_id == 'fleet_vehicle_log_services_action':
                domain = [('vehicle_id', '=', self.id), ('service_type_id.name', '!=', 'Vendor Bill')]
            else:
                domain = [('vehicle_id', '=', self.id)]
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=domain
            )
            return res
        return False
