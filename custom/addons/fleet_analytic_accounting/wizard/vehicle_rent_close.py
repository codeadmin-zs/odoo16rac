from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DT


class WizardRentCloseReason(models.TransientModel):
    _name = 'vehicle.rent.close'

    @api.onchange('additional_fine_ids', 'additional_toll_ids')
    def compute_total_other_charges_cost(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        additional_product_obj = self.env['rental.wizard.fleet.additional.charges']
        salik = fine = 0
        if self.additional_fine_ids:
            for each in self.additional_fine_ids:
                new_additional_product = {'additional_charge_product_id': each.fine_product_id.id,
                                          'unit_measure': each.fine_product_id.uom_id.id,
                                          'unit_price': each.fine_product_id.lst_price,
                                          'product_uom_qty': 1,
                                          'description': each.description or '' + ' - ' + str(each.time_date),
                                          'cost': each.fine_product_id.lst_price,
                                          'agreement_id': tenancy_id.id}
                salik += each.fine_product_id.lst_price
                additional_product_obj.create(new_additional_product)
        if self.additional_toll_ids:
            for each in self.additional_toll_ids:
                new_additional_product = {'additional_charge_product_id': each.salik_product_id.id,
                                          'unit_measure': each.salik_product_id.uom_id.id,
                                          'unit_price': each.salik_product_id.lst_price,
                                          'product_uom_qty': 1,
                                          'description': each.description + ' - ' + str(each.time_date),
                                          'cost': each.salik_product_id.lst_price,
                                          'agreement_id': tenancy_id.id}
                additional_product_obj.create(new_additional_product)
                fine += each.salik_product_id.lst_price
        total_other_charges_cost = salik + fine
        self.total_other_charges_cost = total_other_charges_cost
        tenancy_id.total_other_charges_cost = total_other_charges_cost

    @api.onchange('total_other_charges_cost')
    def compute_invoicing_condition(self):
        if self.total_other_charges_cost > 0:
            self.can_be_invoiced = True
        else:
            self.can_be_invoiced = False

    def _default_vehicle_id_closing(self):
        if self.env.context.get('default_vehicle_id', False):
            return self.env['fleet.vehicle'].browse(self.context.get('default_vehicle_id'))

    def get_toll_ids(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', help="Name of Vehicle.",
                                 track_visibility='onchange', default=_default_vehicle_id_closing)
    salik = fields.Float(string="Salik", required="1")
    fines = fields.Float(string="Fines", required="1")
    total_other_charges_cost = fields.Float(string='Total Other Charges', currency_field='currency_id')
    can_be_invoiced = fields.Boolean(string="Can Be Invoiced?")
    additional_toll_ids = fields.One2many('fleet.vehicle.salik.charges', 'vehicle_close_id',
                                          string='Toll Charge')
    additional_fine_ids = fields.One2many('fleet.vehicle.fine.charges', 'vehicle_close_id',
                                          string='Fine Charge')

    # @api.multi
    def create_invoice_and_close_rent(self):
        rent_obj = self.env['tenancy.rent.schedule']
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        created_rent_obj = rent_obj.create({
            'start_date': datetime.now().strftime(DT),
            'amount': self.total_other_charges_cost,
            'vehicle_id': self.vehicle_id.id,
            'tenancy_id': tenancy_id.id,
            'currency_id': tenancy_id.currency_id.id or False,
            'rel_tenant_id': tenancy_id.tenant_id.id or False
        })

        journal_ids = self.env['account.journal'].search([('type', '=', 'sale')])
        if not tenancy_id.vehicle_id.income_acc_id.id:
            raise Warning(_('Please Configure Income Account from Vehicle.'))

        inv_values = {
            'partner_id': tenancy_id and tenancy_id.tenant_id and tenancy_id.tenant_id.id or False,
            'move_type': 'out_invoice',
            'fleet_vehicle_id': tenancy_id.vehicle_id.id or False,
            'date_invoice': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) or False,
            'journal_id': journal_ids and journal_ids[0].id or False,
            # 'account_id': tenancy_id and tenancy_id.tenant_id.property_account_receivable_id.id or False
        }

        invoice_line_ids_list = []

        if self.total_other_charges_cost > 0:
            inv_line_total_other_charges = {
                'name': 'Fines & Salik',
                'price_unit': self.total_other_charges_cost,
                'quantity': 1,
                'account_id': tenancy_id.vehicle_id.income_acc_id.id or False,
                'analytic_account_id': tenancy_id.vehicle_id.analytic_account_id.id or False,
            }
            invoice_line_ids_list.append((0, 0, inv_line_total_other_charges))

        if len(invoice_line_ids_list) > 0:
            inv_values.update({'invoice_line_ids': invoice_line_ids_list})
            acc_id = self.env['account.move'].create(inv_values)
            created_rent_obj.update({'invc_id': acc_id.id, 'inv': True})
        self.confirm_rent_close()

    # @api.multi
    def confirm_rent_close(self):
        if self._context.get('active_id', False) and self._context.get('active_model', False):
            for reason in self.env[self._context['active_model']].browse(self._context.get('active_id', False)):
                reason.write({'state': 'close',
                              'date_cancel': date.today(),
                              'cancel_by_id': self._uid,
                              'total_other_charges_cost': reason.total_other_charges_cost})
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        return True
