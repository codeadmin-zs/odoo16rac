from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FleetVehicleFinesAndSalik(models.Model):
    _name = 'vehicle.rental.fines'

    amount = fields.Float(string='Amount', required=True)
    time_date = fields.Datetime(string='Date', required=True)
    location = fields.Char(string='Location', required=True)
    description = fields.Text(string='Description')
    analytic_account_id = fields.Many2one('account.analytic.account',
                                          'Analytic Account')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    fine_or_toll = fields.Selection(
        [('0', 'Fine'), ('1', 'Toll')], 'Fine or Toll', default='0', required=True)
    # is_a_fine = fields.Boolean(string='Fine', default=False)
    # is_a_salik = fields.Boolean(string='Salik', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        vals_list[0]['fine_or_toll'] = '0' if vals_list[0]['fine_or_toll'] == 'Fine' else '1'
        vehicle_id = self.env['fleet.vehicle'].browse(vals_list[0]['vehicle_id'])
        additional_product_obj = self.env['rental.wizard.extra.charges']
        if not vals_list[0]['analytic_account_id']:
            fine_or_toll = 'Fines' if vals_list[0]['fine_or_toll'] == 0 else 'Toll Charges'
            fine_or_toll_prod = self.env['product.product'].search([('name', '=', fine_or_toll)])
            self._cr.execute('''
                                SELECT contract.id as contract_id
                                FROM account_analytic_account contract
                                WHERE contract.vehicle_id = %s AND 
                                (contract.date_start <= %s AND 
                                (contract.date >= %s OR (contract.date <= %s AND contract.state = 'open')))
                                    ''', (vals_list[0]['vehicle_id'],
                                          vals_list[0]['time_date'],
                                          vals_list[0]['time_date'],
                                          vals_list[0]['time_date'],))

            for each in self._cr.fetchall():
                analytic_account = self.env['account.analytic.account'].browse(each[0])
                vals_list[0]['analytic_account_id'] = analytic_account.id
                new_additional_product = {'additional_charge_product_id': fine_or_toll_prod.id,
                                          'unit_measure': fine_or_toll_prod.uom_id.id,
                                          'unit_price': vals_list[0]['amount'],
                                          'product_uom_qty': 1,
                                          'description': 'Plate No: ' + vehicle_id.license_plate + ' | Date: ' +
                                                         str(vals_list[0]['time_date']) + ' | Fine Loc.: ' + vals_list[0]['location'] +
                                                         ' | Description: ' + (vals_list[0]['description'] or ''),
                                          'cost': vals_list[0]['amount'],
                                          'agreement_id': analytic_account.id}
                additional_product_obj.create(new_additional_product)

        res = super(FleetVehicleFinesAndSalik, self).create(vals_list)
        return res
