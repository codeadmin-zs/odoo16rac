from odoo import models, fields, _


class RentalOrder(models.Model):
    _inherit = 'sale.order'

    rental_rank = fields.Integer(default=0)


class AccountMoveLineExtend(models.Model):
    _inherit = 'account.move.line'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Tenancy Account')
    description = fields.Text(string='Description')
    payment_done = fields.Boolean(String='Payment done for invoice line', default=False)

    def invoice_payment(self):
        """
        This button method is used to open the related
        account payment form view.
        @param self: The object pointer
        @return: Dictionary of values.
        """
        if not self._ids:
            return []
        for tenancy_rec in self:
            jonral_type = self.env['account.journal'].search([('type', '=', 'cash')])
            # if tenancy_rec.analytic_account_id.acc_pay_dep_rec_id and tenancy_rec.analytic_account_id.acc_pay_dep_rec_id.id:
            #     acc_pay_form_id = self.env['ir.model.data'].get_object_reference('account', 'view_account_payment_form')[1]
            #     print(tenancy_rec, tenancy_rec.acc_pay_dep_rec_id, tenancy_rec.acc_pay_dep_rec_id)
            #     raise Warning(_('Please Enter Advance amount.'))
            #     return {
            #         'view_type': 'form',
            #         'view_id': acc_pay_form_id,
            #         'view_mode': 'form',
            #         'res_model': 'account.payment',
            #         'res_id': self.acc_pay_dep_rec_id.id,
            #         'type': 'ir.actions.act_window',
            #         'target': 'new',
            #         'context': {
            #             'default_partner_id': tenancy_rec.tenant_id.id,
            #             'default_partner_type': 'customer',
            #             'default_journal_id': jonral_type and jonral_type.ids[0] or False,
            #             'default_payment_type': 'inbound',
            #             'default_type': 'receipt',
            #             'default_communication': '',
            #             'default_tenancy_id': tenancy_rec.id,
            #             'default_amount': tenancy_rec.deposit,
            #             'default_property_id':
            #                 tenancy_rec.vehicle_id.id,
            #             'close_after_process': True,
            #         }
            #     }
            ir_id = self.env['ir.model.data']._get_id('account', 'view_account_payment_form')
            ir_rec = self.env['ir.model.data'].browse(ir_id)
            return {
                'view_mode': 'form',
                'view_id': [ir_rec.res_id],
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                'context': {
                    'default_partner_id': tenancy_rec.analytic_account_id.tenant_id.id,
                    'default_partner_type': 'customer',
                    'default_journal_id': jonral_type and jonral_type.ids[0] or False,
                    'default_payment_type': 'inbound',
                    'default_type': 'receipt',
                    'default_communication': tenancy_rec.name,
                    'default_tenancy_id': tenancy_rec.analytic_account_id.id,
                    'default_amount': tenancy_rec.price_total,
                    'default_property_id': tenancy_rec.analytic_account_id.vehicle_id.id,
                    'close_after_process': True,
                }
            }
