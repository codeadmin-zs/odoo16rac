from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from langdetect import detect
import logging
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class CompanyVatConfig(models.Model):
    _inherit = 'res.company'

    def _get_default_company_name(self):
        if self.name:
            self.taxable_name_english = self.name

    vat_enabled = fields.Boolean(related='country_id.vat_enabled', default=False)
    taxable_name_english = fields.Char(string='Taxable Person Name (English)', default=_get_default_company_name, store=True)
    company_name_arabic = fields.Char(string='Taxable Person Name (Arabic)', store=True)
    tax_agency_name = fields.Char(string='Tax Agency Name', store=True)
    tan = fields.Char(string='TAN', store=True)
    tax_agent_name = fields.Char(string='Tax Agent Name', store=True)
    taan = fields.Char(string='TAAN', store=True)
    vat_tax = fields.Char(string="VAT NO/TRN No", help="Vat/TRN number")

    # Onchange Check if the company name in arabic has entered
    @api.onchange('company_name_arabic')
    def _do_arabic_check_onchange(self):
        warning = {}
        if self.company_name_arabic:
            vaal = self.company_name_arabic
            vaal = vaal.replace(" ", "")
            vaal = vaal.replace(".", "")
            lang = detect(vaal)
            if lang != "fa" and lang != "ar":
                return {'warning': {'title': _('Error'), 'message': _('Value should be in arabic'), }, }

    # Check if the company name in arabic has entered
    @api.constrains('company_name_arabic')
    def _do_arabic_check(self):
        if self.company_name_arabic:
            vaal = self.company_name_arabic
            vaal = vaal.replace(" ", "")
            vaal = vaal.replace(".", "")
            lang = detect(vaal)
            if lang != "fa" and lang != "ar":
                raise ValidationError("Value should be in arabic")


class CountryVatConfig(models.Model):
    _inherit = 'res.country'

    vat_enabled = fields.Boolean(string="VAT")


class PartnerVatConfig(models.Model):
    _inherit = 'res.partner'

    state_id = fields.Many2one(required=True)
    country_id = fields.Many2one(required=True)


class AccountInvoiceInherited(models.Model):
    _inherit = "account.move"

    def _compute_val(self):
        if self.invoice_line_ids and self.reverse_charges:
            for line in self.invoice_line_ids:
                if line.invoice_line_tax_ids:
                    inv_tax_transfer_account_tax_id = line.invoice_line_tax_ids[0]
            self.inv_tax_transfer_account = inv_tax_transfer_account_tax_id.account_id.id

    date_invoice = fields.Date(string='Invoice Date', readonly=True, states={'draft': [('readonly', False)]},
                               index=True, help="Keep empty to use the current date",
                               copy=False, track_visibility='always')
    amount_tax = fields.Monetary(string='VAT', store=True, readonly=True,
                                 compute='_compute_amount', track_visibility='always')
    permit_no = fields.Char(string='Permit Number', store=True)
    vat = fields.Char(related='partner_id.vat', string="TRN", readonly=True, help="Tax Registration Number")
    reverse_charges = fields.Boolean(string='Reverse Charges')
    paid_customs_duty = fields.Boolean(string='Imported through UAE customs')
    cust_state = fields.Char(string='State')
    cust_country = fields.Char(string='Country')
    bank_account = fields.Many2one('account.journal', string='Bank', ondelete='restrict')
    customs_duty = fields.Float(string='Customs Duty')
    invoice_history_ids = fields.One2many('account.invoice.history', 'invoice_id', string='Invoice History', copy=False)

    # @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.invoice_line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity,
                                                          line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
                tax_object = self.env['account.tax']
                tax_line_object = tax_object.search([('id', '=', tax['id'])])

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']

                # Add negative tax amount to transfer account if reverse charge is selected
                if self.reverse_charges:
                    if tax_line_object.tax_transfer_account:
                        tax_object = self.env['account.tax']
                        tax['account_id'] = tax_line_object.tax_transfer_account.id
                        amount = tax['amount']
                        tax['amount'] = (-1) * amount
                        val = self._prepare_tax_line_vals(line, tax)
                        key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                        if key not in tax_grouped:
                            tax_grouped[key] = val
                        else:
                            tax_grouped[key]['amount'] += val['amount']
                            tax_grouped[key]['base'] += val['base']
        return tax_grouped

    @api.onchange('partner_id')
    def _onchange_trn(self):
        if self.partner_id:
            partner_id = self.partner_id.id
            trn = self.env['res.partner'].search([('id', '=', partner_id)]).vat
            self.vat = trn
            self.cust_state = self.env['res.partner'].search([('id', '=', partner_id)]).state_id.name
            self.cust_country = self.env['res.partner'].search([('id', '=', partner_id)]).country_id.name


# capture invoice modification history
class AccountInvoiceHistory(models.Model):
    _name = "account.invoice.history"
    _description = "Invoice History"
    _order = "invoice_id,id"

    invoice_id = fields.Many2one('account.move', string='Invoice')
    status = fields.Char(string="Status", store=True, help="Invoice Status")
    update_date = fields.Date(string='Modification Date', default=datetime.now())
    invoice_amount = fields.Float(string='Amount', digits=dp.get_precision('Product Price'))


class AccountTaxInherited(models.Model):
    _inherit = "account.tax"

    tax_code = fields.Char(string='Tax Code', store='true')
    tax_transfer_account = fields.Many2one('account.account', string='Transfer Account', ondelete='restrict')


class AccountJournalInherited(models.Model):
    _inherit = "account.journal"

    iban_number = fields.Char(string='IBAN Number', store='true')
    branch_name = fields.Char(string='Branch Name', store='true')


class AccountMoveLineInherited(models.Model):
    _inherit = "account.move.line"

    tax_id = fields.Many2one('account.tax', string='VAT', ondelete='restrict')
    invoice_line_tax_ids = fields.Many2many('account.tax',
                                            'account_invoice_line_tax', 'invoice_line_id', 'tax_id',
                                            string='VAT',
                                            domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                                                    ('active', '=', True)], oldname='invoice_line_tax_id')


class AccountFafReport(models.TransientModel):
    _name = "faf.report"
    _description = "Account FAF Report"

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # @api.one
    # @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id')
    def _compute_payment_difference(self):
        if len(self.invoice_ids) == 0:
            return
        if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
            self.payment_difference = self.amount - self._compute_total_invoices_amount()
            self.payment_actual = self._compute_total_invoices_amount()
        else:
            self.payment_difference = self._compute_total_invoices_amount() - self.amount
            self.payment_actual = self._compute_total_invoices_amount()

    payment_actual = fields.Monetary(compute='_compute_payment_difference', string="Actual amount to pay", readonly=True)
    #auto populate reverse charge amount in write_off field and minus tax amount from sum
