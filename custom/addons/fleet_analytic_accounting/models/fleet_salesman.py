# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api,  _
from odoo.addons.base.models import decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, ustr


class FleetSalesMan(models.Model):
    _name = 'fleet.salesman'

    # @api.multi
    def return_action_for_open(self):
        """ This opens the xml view specified in xml_id \
        for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id('fleet_analytic_accounting.' + xml_id)
            res.update(
                context=dict(self.env.context,
                             default_manager_id=self.related_user_id.id, group_by=False),
                domain=[('manager_id', '=', self.related_user_id.id)]
            )
            return res
        return False

    # @api.multi
    def action_view_invoice(self):
        """ This opens the xml view specified in xml_id \
        for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id('account.' + xml_id)
            res.update(
                context=dict(self.env.context,
                             default_user_id=self.related_user_id.id, group_by=False),
                domain=[('user_id', '=', self.related_user_id.id)]
            )
            return res
        return False

    # @api.multi
    def _count_rent(self):
        """ This method count the total number of \
        rent for the current vehicle """
        rent_obj = self.env['account.analytic.account']
        for record in self:
            record.rent_count = \
                rent_obj.search_count([('manager_id', '=', record.related_user_id.id)])

    # @api.multi
    def _invoice_rent(self):
        """ This method count the total number of \
        rent for the current vehicle """
        rent_obj = self.env['account.move']
        for record in self:
            record.invoice_count = \
                rent_obj.search_count([('user_id', '=', record.related_user_id.id), ('move_type', '=', 'out_invoice')])

    # @api.one
    def _compute_invoice_ids(self):
        # get recordset of related object, for example with search (or whatever you like):
        for record in self:
            related_recordset = self.env["account.move"].search([('user_id', '=', record.related_user_id.id),
                                                                 ('move_type', '=', 'out_invoice'),
                                                                 ('state', '=', 'paid')])
            self.invoice_ids = related_recordset

    # @api.one
    def _compute_customer_ids(self):
        # get recordset of related object, for example with search (or whatever you like):
        for record in self:
            related_recordset = self.env["res.partner"].search([('user_id', '=', record.related_user_id.id)])
            self.customer_ids = related_recordset

    account_receivable_id = fields.Many2one("account.account",string="Account Receivable")
    account_payable_id = fields.Many2one("account.account",string="Account Payable")
    expence_acc_id = fields.Many2one("account.account",string="Expense Account")
    first_name = fields.Char(string="First Name")
    last_name = fields.Char(string="Last Name")
    # commission_percentage = fields.Float(string="Commission %",digits=dp.get_precision('Product Price'))
    commission_percentage = fields.Float(string='Commission %', digits=dp.get_precision('Product Price'))
    # customer_line_ids = fields.One2many
    # customer_ids = fields.One2many('fleet.salesman.customers', 'partner_id', string='Customers')
    related_user_id = fields.Many2one(comodel_name='res.users',string='Related User',
                                      help="The user correspond to this salesman.")
    rent_count = fields.Integer(compute='_count_rent', string="Rents")
    invoice_count = fields.Integer(compute='_invoice_rent', string="Invoices")
    invoice_ids = fields.One2many('account.move', 'user_id', string='Invoices', compute="_compute_invoice_ids")
    customer_ids = fields.One2many('res.partner', 'user_id', string='Customers', compute="_compute_customer_ids")


class FleetSalesManCustomers(models.Model):
    _name = 'fleet.salesman.customers'

    sales_man_id = fields.Many2one(
        comodel_name='fleet.salesman',
        string='Salesman')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Partner')


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    # @api.one
    def _compute_commission(self):
        # get recordset of related object, for example with search (or whatever you like):
        salesman_obj = self.env['fleet.salesman']
        for record in self:
            sales_man_id = record.user_id.id
            commission_percentage = salesman_obj.search([('related_user_id', '=', sales_man_id)]).commission_percentage
            if commission_percentage:
                commission = record.amount_total_signed*(commission_percentage/100)
                self.commission_amount = commission

    # @api.one
    def _compute_fleet_salesman(self):
        # get recordset of related object, for example with search (or whatever you like):
        salesman_obj = self.env['fleet.salesman']
        for record in self:
            sales_man_id = record.user_id.id
            fleet_sales_man_id = salesman_obj.search([('related_user_id', '=', sales_man_id)]).id
            if fleet_sales_man_id:
                self.fleet_sales_man_id = fleet_sales_man_id

    commission_generated = fields.Boolean(default=False)
    commission_paid = fields.Boolean(default=False)
    commission_amount = fields.Float(string='Commission', compute="_compute_commission")
    fleet_sales_man_id = fields.Many2one("fleet.salesman", string="Fleet Salesman",compute="_compute_fleet_salesman")
    invc_id = fields.Many2one(comodel_name='account.move', string='Vendor Bill')

    # @api.multi
    # def return_action_to_generate_commission(self):
    #     """ This opens the xml view specified in xml_id \
    #     for the current vehicle """
    #     # self.ensure_one()
    #     # xml_id = self.env.context.get('xml_id')
    #     # if xml_id:
    #     #     res = self.env['ir.actions.act_window'].for_xml_id(
    #     #         'fleet_rent', xml_id)
    #     #     res.update(
    #     #         context=dict(self.env.context,
    #     #                      default_manager_id=self.related_user_id.id, group_by=False),
    #     #         domain=[('manager_id', '=', self.related_user_id.id)]
    #     #     )
    #     #     return res
    #     return True

    # @api.multi
    def return_action_to_generate_commission(self):
        """
        Create invoice for Rent Schedule.
        """
        journal_ids = self.env['account.journal'].search(
            [('type', '=', 'purchase')])
        if not self.fleet_sales_man_id.expence_acc_id.id:
            raise Warning(_('Please Configure Expense Account for Salesman.'))
        if not self.fleet_sales_man_id.account_payable_id.id:
            raise Warning(_('Please Configure Payable Account for Salesman.'))
        inv_line_main = {
            'origin': self.number,
            'name': 'Sales Commission For'+self.fleet_sales_man_id.first_name,
            'price_unit': self.commission_amount or 0.00,
            'quantity': 1,
            'account_id': self.fleet_sales_man_id.expence_acc_id.id or False,
        }
        # if self.tenancy_id.multi_prop:
        #     for data in self.tenancy_id.prop_id:
        #         for account in data.property_ids.income_acc_id:
        #             inv_line_main.update({'account_id': account.id})

        inv_line_values = {
            # 'origin': self.number,
            'name': 'Sales Commission For'+self.fleet_sales_man_id.first_name,
            'price_unit': self.commission_amount or 0.00,
            'quantity': 1,
            'account_id': self.fleet_sales_man_id.expence_acc_id.id or False,
        }
        # if self.tenancy_id.multi_prop:
        #     for data in self.tenancy_id.prop_id:
        #         for account in data.property_ids.income_acc_id:
        #             inv_line_values.update({'account_id': account.id})
        inv_values = {
            'partner_id': self.user_id.id or False,
            'move_type': 'in_invoice',
            # 'vehicle_id': self.tenancy_id.vehicle_id.id or False,
            'invoice_date': datetime.now().strftime(
                DEFAULT_SERVER_DATE_FORMAT) or False,
            'journal_id': journal_ids and journal_ids[0].id or False,
            # 'account_id': self.fleet_sales_man_id.account_payable_id.id
            # or False
        }
        # if self.tenancy_id.main_cost:
        #     inv_values.update({'invoice_line_ids': [(0, 0, inv_line_values),
        #                                             (0, 0, inv_line_main)]})
        # else:
        #     inv_values.update(
        #         {'invoice_line_ids': [(0, 0, inv_line_values)]})
        inv_values.update({'invoice_line_ids': [(0, 0, inv_line_values)]})
        acc_id = self.env['account.move'].create(inv_values)
        self.write({'invc_id': acc_id.id})
        self.write({'commission_generated': True})
        context = dict(self._context or {})
        wiz_form_id = self.env['ir.model.data'].get_object_reference(
            'account', 'invoice_supplier_form')[1]

        return {
            'view_type': 'form',
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invc_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': context,
        }

    # @api.multi
    def return_action_to_view_commission(self):
        """
        This Method is used to Open invoice
        @param self: The object pointer
        """
        context = dict(self._context or {})
        wiz_form_id = self.env['ir.model.data'].get_object_reference(
            'account', 'invoice_supplier_form')[1]
        return {
            'view_type': 'form',
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invc_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': context,
        }
