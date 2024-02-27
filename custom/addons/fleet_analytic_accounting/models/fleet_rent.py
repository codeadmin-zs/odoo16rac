from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

class AccountInvoice(models.Model):
    _inherit = "account.move"

    new_tenancy_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Rental Vehicle')


class AccountPaymentExtend(models.Model):
    _inherit = 'account.payment'

    tenancy_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Rental Vehicle',
        help='Rental Vehicle Name.')


class AccountpaymentExtend(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        res = super(AccountpaymentExtend, self).action_create_payments()
        active_id = self._context.get('active_id')
        account_obj = self.env['account.asset.asset']

        inv_obj = self.env['account.move']
        tenancy_invoice_rec = inv_obj.browse(self._context['active_ids'])
        if tenancy_invoice_rec.invoice_origin:
            p_id = self.env['purchase.order'].search([('name', '=', tenancy_invoice_rec.invoice_origin)])
            asset_id = account_obj.search([('purch_id', '=', p_id.id)])
            origin_name = self.env['account.move'].search([('invoice_origin', '=', tenancy_invoice_rec.invoice_origin)])
            asset_id.vendor_ref = origin_name.id
            asset_id.vendor_date = origin_name.invoice_date

            analy_id = self.env['account.analytic.account'].search([('id', '=', asset_id.analytic_account_id.ids)])
            for rec in analy_id:
                self.env['account.analytic.line'].create(
                    {'name': 'Vendor Bill Payment', 'account_id': rec.id, 'date': origin_name.invoice_date,
                     'amount': rec.vehicle_id.vehicle_cost_price})

        tenancy_rent_obj = self.env['tenancy.rent.schedule']
        for invoice in tenancy_invoice_rec:
            rent_sched_ids = tenancy_rent_obj.search([('invc_id', '=', invoice.id)])
            for rent_sched_rec in rent_sched_ids:
                if rent_sched_rec.invc_id:
                    amt = rent_sched_rec.invc_id.amount_residual or 0.0
                rent_sched_rec.write({'pen_amt': amt})
                if rent_sched_rec.invc_id.state == 'posted':
                    rent_sched_rec.paid = True
                    rent_sched_rec.move_check = True
                    if rent_sched_rec.tenancy_id.extra_charges_ids or \
                            rent_sched_rec.tenancy_id.additional_rental_charges_ids:
                        for each in rent_sched_rec.tenancy_id.extra_charges_ids:
                            each.line_added_status = True
                        for each in rent_sched_rec.tenancy_id.additional_rental_charges_ids:
                            each.line_added_status = True
            if self._context.get('return', False) and self._context.get('active_model', False) and self._context[
                'active_model'] == 'account.move':
                for invoice in self.env[self._context['active_model']].browse(
                        self._context.get('active_id', False)):
                    if invoice.new_tenancy_id:
                        invoice.new_tenancy_id.write({
                            'deposit_return': True,
                            'amount_return': invoice.amount_total})
        return res


#filter in vehicle
class FleetVehicleLogServicesFilter(models.Model):
    _inherit = "fleet.vehicle.log.services"

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True, help='Vehicle concerned by this log',
                                 domain="[('state_id.name', 'in', ['Available', 'In shop'])]")

# changing state while canceling the PO


class SaleOrderCancel(models.Model):
    _inherit = 'sale.order'

    def action_cancel(self):
        sale_order_id = self.id
        product_template_id = product_id_ = self.env['sale.order.line'].search([('order_id', '=', sale_order_id)]).product_id.product_tmpl_id.id
        fleet_vehicle_obj = self.env['fleet.vehicle'].search([('vehicle_prodcut_template_id', '=', product_template_id)])
        account_analytic_account_obj = self.env['account.analytic.account'].search([('sale_order_id', '=', sale_order_id), ('state', '!=', 'close')])
        state_id = self.env['fleet.vehicle.state'].search([('name', '=', 'Available')]).id
        for account_analytic_account_obj_each in account_analytic_account_obj:
            fleet_vehicle_id = self.env['fleet.vehicle'].search(
                [('id', '=', account_analytic_account_obj_each.vehicle_id.id)])
            record_fleet_vehicle = self.env['fleet.vehicle'].search([('id', '=', fleet_vehicle_id.id)])
            record_fleet_vehicle.write({'state_id': state_id, 'state': 'complete'})

            fleet_vehicle_id = self.env['fleet.vehicle'].search([('id', '=', account_analytic_account_obj_each.vehicle_id.id)])
            record_fleet_vehicle = self.env['fleet.vehicle'].search([('id', '=', fleet_vehicle_id.id)])
            record_fleet_vehicle.write({'state_id': state_id, 'state': 'complete'})

            record_account_analytic_account = self.env['account.analytic.account'].search([('id', '=', account_analytic_account_obj_each.id)])
            record_account_analytic_account.write({'state': 'close'})

        super(SaleOrderCancel, self).action_cancel()



class NonEditableInheritedFleetVehicleState(models.Model):
    _inherit = 'fleet.vehicle.state'
    _description = 'Vehicle Status'

    @api.model
    def create(self, vals):
        raise ValidationError('You cannot create records of this type.')

    def write(self, vals):
        raise ValidationError('You cannot edit records of this type.')

    def unlink(self):
        raise ValidationError('You cannot delete records of this type.')

class SaleOrderInherited(models.Model):
    _inherit = 'sale.order'

    validity_date = fields.Date(
        string='Expiration',
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=lambda self: (fields.Date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    )
    invoice_policies_temp = fields.Selection(
        [("advanced", "Advance Invoicing"), ("periodic", "Periodic Invoicing"), ("post_invoicing", "Post Invoicing"), ],
        string="Invoicing Policy", required=True, default="advanced")

    @api.constrains('validity_date')
    def _check_validity_date(self):
        for order in self:
            if order.validity_date and order.validity_date < fields.Date.today():
                raise ValidationError("Expiration date cannot be in the past..")

    @api.onchange('rental_term')
    def _onchange_invoice_policies(self):
        if self.rental_term == 'long_term':
            self.invoice_policies_temp = 'periodic'
