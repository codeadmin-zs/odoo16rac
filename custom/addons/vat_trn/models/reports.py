# -*- coding: utf-8 -*-
##############################################################################
#Author: Zaeem Soultions
#Purpose Backend logic for FAF Report
##############################################################################
from io import StringIO
import csv
import codecs

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class AccountUnicodeWriter(object):

    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        # created a writer with Excel formating settings
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        # we ensure that we do not try to encode none or bool
        row = (x or u'' for x in row)

        encoded_row = [
            c.encode("utf-8") if isinstance(c, str) else c for c in row]

        self.writer.writerow(encoded_row)
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        # data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class AccountCSVExport(models.TransientModel):
    _name = 'csv.export'
    _description = 'Generate Reports'

    data_string = fields.Text('Data')
    data = fields.Binary('CSV', readonly=True, attachment=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    export_filename = fields.Char('Export CSV Filename', default='faf_report.csv', size=128)

    def action_manual_export_journal_entries(self):
        return self.env.ref('vat_trn.faf_report_xlsx').report_action(self, data={}, config=False)

    # FAF report Fields Static content
    def _get_header_compinfo(self):
        comp_info_start = ['CompInfoStart']
        return comp_info_start

    def _get_footer_compinfo(self):
        comp_info_end = ['CompInfoEnd']
        return comp_info_end

    def _get_header_journal_entries(self):
        if str(self.company_id.currency_id.name) == 'AED':
            trn_or_vat = 'TRN'
        else:
            trn_or_vat = 'VAT ID'
        file_headers = [
            'TaxablePersonNameEn',
            'TaxablePersonNameAr',
            trn_or_vat,
            'TaxAgencyName',
            'TAN',
            'TaxAgentName',
            'TAAN',
            'PeriodStart',
            'PeriodEnd',

            # Other fields
            'FAFCreationDate',
            'ProductVersion',
            'FAFVersion',
        ]
        return file_headers

    def _get_header_vendor_bills(self):
        file_headers = [
            'SupplierName',
            'SupplierTIN/TRN',
            'InvoiceDate',
            'InvoiceNo',
            'PermitNo',
            'LineNo',
            'ProductDescription',
            'PurchaseValueAED',
            'VATValueAED',
            'TaxCode',
            'FCY Code',
            'PurchaseFCY',
            'AEDFCY',
        ]
        return file_headers

    def _get_header_PurcDataStart(self):
        PurcDataStart = ['PurcDataStart']
        return PurcDataStart

    def _get_header_SuppDataStart(self):
        SuppDataStart = ['SuppDataStart']
        return SuppDataStart

    def _get_footer_vendor_bills(self):
        file_headers = [
            'PurcDataEnd',
            'PurchaseTotalAED',
            'VATTotalAED',
            'TransactionCountTotal',
        ]
        return file_headers

    def _get_header_invoices(self):
        file_headers = [
            'Customer Name',
            'CustomerTIN/TRN',
            'InvoiceDate',
            'InvoiceNo',
            'LineNo',
            'ProductDescription',
            'SupplyValueAED',
            'VATValueAED',
            'TaxCode',
            'Country',
            'FCYCode',
            'SupplyFCY',
            'VATFCY',
        ]
        return file_headers

    def _get_footer_invoices(self):
        file_headers = [
            'SuppDataEnd',
            'SupplyTotalAED',
            'VATTotalAED',
            'TransactionCountTotal',
        ]
        return file_headers

    def _get_header_GLDataStart(self):
        GLDataStart = ['GLDataStart']
        return GLDataStart

    def _get_header_gl(self):
        file_headers = [
            'TransactionDate',
            'AccountID',
            'AccountName',
            'TransactionDescription',
            'Name',
            'TransactionID',
            'SourceDocumentID',
            'SourceType',
            'Debit',
            'Credit',
            'Balance',
        ]
        return file_headers

    def _get_footer_gl(self):
        footers = ['GLDataEnd', 'TotalDebit', 'TotalCredit', 'TransactionCountTotal', 'GLTCurrency']
        return footers

    # Get report parameters from form
    def get_data(self, result_type):
        date_from = self.date_from
        date_to = self.date_to
        company_id = self.company_id.id
        self._cr.execute("""
                SELECT
                  taxable_name_english as english_name,
                  company_name_arabic AS arabic_name,
                  vat_tax AS trn,
                  tax_agency_name AS tax_agency,
                  tan AS tan,
                  tax_agent_name AS tax_agent,
                  taan AS taan,
                  to_char(date %s, 'DD-MM-YYYY') AS date_from,
                  to_char(date %s, 'DD-MM-YYYY') AS date_to,
                  to_char(NOW(), 'DD-MM-YYYY') AS FAFCreationDate,
                  '1.0' AS ProductVersion,
                  'FAFv1.0.0' AS FAFVersion
                FROM
                  public.res_company
                WHERE res_company.id = %s
                """, (date_from, date_to, company_id))
        rows = self._cr.dictfetchall()
        return rows

    # Convert all fetched data for csv export iteration
    def get_vendor_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        comp = self.env['res.company'].browse(company_id)
        companies = self.env['res.company'].search([('currency_id', '=', comp.currency_id.id)])
        self._cr.execute("""SELECT partner.name AS partner,
                            partner.vat AS vat,
                            to_char(date(am.date_invoice), 'DD-MM-YYYY') AS billdate,
                            am.name AS invoice_number,
                            am.permit_no AS permit_number,
                            aml.sequence AS sequence_number,
                            aml.name AS ail_name, 
                            ROUND(aml.price_subtotal,2) AS price_aed,
                            ROUND((aml.price_subtotal/100)*at.amount,2) AS tax_amount,
                            at.tax_code,
                            currency.name,
                            aml.price_subtotal,
                            (aml.price_subtotal/100)*at.amount AS AEDFCY,
                            am.move_type AS ai_type
                            FROM account_move_line aml
                            JOIN account_move am ON am.id = aml.move_id
                            JOIN res_partner partner ON am.commercial_partner_id = partner.id
                            LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = aml.id
                            LEFT JOIN account_tax at ON at.id = ailt.tax_id
                            LEFT JOIN res_currency currency ON currency.id = am.currency_id
                            LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                            LEFT JOIN product_product pr ON pr.id = aml.product_id
                            WHERE am.move_type IN ('in_invoice','in_refund')  AND am.state IN ('open','paid') 
                            AND am.company_id IN %s AND am.date_invoice BETWEEN %s AND %s
                            GROUP BY partner.name,partner.vat,am.date_invoice, am.name,am.permit_no,
                            aml.sequence,aml.name, aml.price_subtotal,am.id,ailt.invoice_line_id,at.id,
                            ailt.tax_id,am.currency_id,currency.name,currency.id,cr_rate.rate
                            ORDER BY partner.name,am.name,am.id""", (tuple(companies.ids), date_from, date_to))

        rows2 = self._cr.dictfetchall()

        self._cr.execute("""SELECT COALESCE(partner.name,aml.name) AS partner,
                            partner.vat AS vat,
                            to_char(date(aml.date), 'DD-MM-YYYY') AS billdate,
                            am.name AS invoice_number,
                            am.permit_no AS permit_number,
                            aml.sequence AS sequence_number,
                            aml.name AS ail_name, 
                            ROUND(aml.price_subtotal,2) AS price_aed,
                            ROUND((aml.price_subtotal/100)*at.amount,2) AS tax_amount,
                            at.tax_code, 
                            currency.name, 
                            aml.price_subtotal,
                            (aml.price_subtotal/100)*at.amount AS AEDFCY,
                            am.move_type AS ai_type
                            FROM account_move_line AS aml
                            JOIN account_account AS aa on aa.id=aml.account_id
                            JOIN account_account_type AS aat on aat.id=aa.user_type_id
                            JOIN account_journal AS aj on aj.id = aml.journal_id
                            LEFT JOIN account_move AS am on am.id=aml.move_id
                            LEFT JOIN res_partner partner ON partner.id = am.partner_id
                            LEFT JOIN account_tax AS at ON at.id = aml.tax_line_id
                            LEFT JOIN res_currency AS currency ON currency.id = am.currency_id
                            WHERE aa.company_id in %s AND aml.date BETWEEN %s AND %s 
                            AND aa.name = 'Taxes Paid' AND aj.type = 'cash'
                            GROUP BY aml.date,aa.code,aa.name,
                            aml.name,aj.name,aml.price_subtotal,
                            am.name,am.name,aat.name,aml.debit,
                            aml.credit,aml.move_id,partner.name,aml.sequence,am.move_type,
                            partner.vat, at.amount,at.tax_code, currency.name, am.permit_no
                            ORDER BY aml.date,aml.move_id""", (tuple(companies.ids), date_from, date_to))

        rows4 = self._cr.dictfetchall()
        return rows2 + rows4

    def get_vendor_footer_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        comp = self.env['res.company'].browse(company_id)
        companies = self.env['res.company'].search([('currency_id', '=', comp.currency_id.id)])
        self._cr.execute("""SELECT 'PurcDataEnd' AS PurcDataEnd,
                            SUM(ROUND(aml.price_subtotal,2)) AS PurchaseTotalAED,
                            ROUND(SUM((aml.price_subtotal/100)*at.amount),2) AS VATTotalAED,
                            COUNT(DISTINCT am.id) AS TransactionCountTotal,
                            am.move_type AS ai_type
                            FROM account_move_line aml
                            JOIN account_move am ON am.id = aml.move_id
                            JOIN res_partner partner ON am.commercial_partner_id = partner.id
                            LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = aml.id
                            LEFT JOIN account_tax at ON at.id = ailt.tax_id
                            LEFT JOIN res_currency currency ON currency.id = am.currency_id
                            LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                            LEFT JOIN product_product pr ON pr.id = aml.product_id
                            WHERE am.move_type IN ('in_invoice','in_refund')  AND am.state IN ('open','paid') 
                            AND am.company_id IN %s AND am.date_invoice BETWEEN %s AND %s
                            GROUP BY am.move_type""", (tuple(companies.ids), date_from, date_to))

        bill_total = 0
        bill_total_tax = 0
        bill_refund_total = 0
        bill_refund_total_tax = 0
        transaction_count = 0
        rows2 = self._cr.dictfetchall()
        for row in rows2:
            # msg1 = ("This is my debug message row! %s", row)
            # _logger.error(msg1)
            if row['ai_type'] == "in_invoice":
                bill_total = bill_total + row['purchasetotalaed']
                if row['vattotalaed']:
                    bill_total_tax = bill_total_tax + row['vattotalaed']
                transaction_count = transaction_count + row['transactioncounttotal']
            elif row['ai_type'] == "in_refund":
                bill_refund_total = bill_refund_total + row['purchasetotalaed']
                # bill_refund_total_tax = bill_refund_total_tax+row['vattotalaed']
                if row['vattotalaed']:
                    bill_refund_total_tax = bill_refund_total_tax + row['vattotalaed']
                transaction_count = transaction_count + row['transactioncounttotal']

        bill_refund_total_negative = -1 * bill_refund_total
        bill_refund_total_tax_negative = -1 * bill_refund_total_tax
        total_purchase_amount = bill_total + bill_refund_total_negative
        total_purchase_tax_amount = bill_total_tax + bill_refund_total_tax_negative

        self._cr.execute("""SELECT 'PurcDataEnd' AS PurcDataEnd,
                            SUM(ROUND(aml.price_subtotal,2)) AS PurchaseTotalAED,
                            ROUND(SUM((aml.price_subtotal/100)*at.amount),2) AS VATTotalAED,
                            COUNT(DISTINCT am.id) AS TransactionCountTotal,
                            am.move_type AS ai_type
                            FROM account_move_line AS aml 
                            JOIN account_account AS aa on aa.id=aml.account_id
                            JOIN account_account_type AS aat on aat.id=aa.user_type_id
                            JOIN account_journal AS aj on aj.id = aml.journal_id
                            LEFT JOIN account_move AS am on am.id=aml.move_id
                            LEFT JOIN res_partner partner ON partner.id = am.partner_id
                            LEFT JOIN account_tax AS at ON at.id = aml.tax_line_id
                            LEFT JOIN res_currency AS currency ON currency.id = am.currency_id
                            WHERE aa.company_id IN %s AND aml.date BETWEEN %s AND %s 
                            AND aa.name = 'Taxes Paid' AND aj.type = 'cash'
                            GROUP BY aml.date,aa.code,aa.name,aml.name,aj.name,
                            am.name,am.name,aat.name,aml.debit,aml.credit,am.move_type,
                            aml.move_id,partner.name,partner.vat,at.tax_code, currency.name
                            ORDER BY aml.date,aml.move_id""",
                         (tuple(companies.ids), date_from, date_to))

        bill_total_petty = 0
        bill_total_tax_petty = 0
        transaction_count_petty = 0
        rows2_tuple = ""
        while 1:
            self._cr.arraysize = 100
            rows2 = self._cr.fetchmany()
            if not rows2:
                break
            for row in rows2:
                msg1 = ("This is my debug message row! %s", row)
                _logger.error(msg1)
                bill_total_petty += row[1]
                bill_total_tax_petty += row[2] if row[2] > 0.0 else row[3]
                transaction_count_petty += row[0]
        rows = {
            'purchase_data_end': 'PurcDataEnd',
            'total_purchase_amount': total_purchase_amount + bill_total_petty,
            'total_purchase_tax_amount': total_purchase_tax_amount + bill_total_tax_petty,
            'transaction_count': transaction_count + transaction_count_petty,
        }
        return rows

    def get_invoice_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT partner.name AS partner,partner.vat AS vat,
                            to_char(date(ai.date_invoice), 'DD-MM-YYYY') AS invoicedate,ai.name AS invoice_number,ail.sequence AS sequence_number,
                            ail.name AS ail_name,ROUND(ail.price_subtotal*((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)),2) AS price_aed,ROUND((((ail.price_subtotal/100)*at.amount) * ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)) ),2)AS tax_amount_aed,at.tax_code AS tax_code,
                            country.name AS country,currency.name AS currency,ail.price_subtotal AS price_subtotal,((ail.price_subtotal/100)*at.amount) AS tax_amount,ai.move_type AS ai_type
                        FROM account_move_line ail
                        JOIN account_move ai ON ai.id = ail.move_id
                        LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                        LEFT JOIN account_tax at ON at.id = ailt.tax_id
                        LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                        LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                        JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                        JOIN res_country country ON partner.country_id = country.id
                        LEFT JOIN product_product pr ON pr.id = ail.product_id
                        WHERE ai.move_type IN ('out_invoice','out_refund') AND ai.state IN ('open','paid') AND ai.company_id = %s AND ai.date_invoice BETWEEN %s AND %s
                        GROUP BY partner.name,partner.vat,ai.date_invoice, ai.name,ail.sequence,ail.name, ail.price_subtotal,ai.id,country.name,ailt.invoice_line_id,at.id,ailt.tax_id,
                        ai.currency_id,currency.name,currency.id,cr_rate.rate
                        ORDER BY partner.name,ai.name,ai.id""", (company_id, date_from, date_to))
        rows = self._cr.dictfetchall()
        return rows

    def get_invoices_footer_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT 'CustDataEnd' AS CustDataEnd,SUM(ROUND(ail.price_subtotal*((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)),2)) AS SupplyTotalAED,
                            ROUND(SUM((((ail.price_subtotal/100)*at.amount) * ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)) )),2) AS VATTotalAED,COUNT(DISTINCT ai.id) AS TransactionCountTotal, ai.move_type AS ai_type
                        FROM account_move_line ail
                        JOIN account_move ai ON ai.id = ail.move_id
                        JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                        LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                        LEFT JOIN account_tax at ON at.id = ailt.tax_id
                        LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                        LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                        LEFT JOIN product_product pr ON pr.id = ail.product_id
                        WHERE ai.move_type IN ('out_invoice','out_refund')  AND ai.state IN ('open','paid') AND ai.company_id = %s AND ai.date_invoice BETWEEN %s AND %s
                        GROUP BY ai.move_type""", (company_id, date_from, date_to))
        rows2 = self._cr.dictfetchall()
        bill_total = 0
        bill_total_tax = 0
        bill_refund_total = 0
        bill_refund_total_tax = 0
        transaction_count = 0
        for row in rows2:
            if row['ai_type'] == "out_invoice":
                bill_total = bill_total + row['supplytotalaed']
                bill_total_tax = bill_total_tax + row['vattotalaed']
                transaction_count = transaction_count + row['transactioncounttotal']
            elif row['ai_type'] == "out_refund":
                bill_refund_total = bill_refund_total + row['supplytotalaed']
                bill_refund_total_tax = bill_refund_total_tax + row['vattotalaed']
                transaction_count = transaction_count + row['transactioncounttotal']

        bill_refund_total_negative = -1 * bill_refund_total
        bill_refund_total_tax_negative = -1 * bill_refund_total_tax
        total_purchase_amount = bill_total + bill_refund_total_negative
        total_purchase_tax_amount = bill_total_tax + bill_refund_total_tax_negative
        rows = {
                'purchase_data_end': 'CustDataEnd',
                'total_purchase_amount': total_purchase_amount,
                'total_purchase_tax_amount': total_purchase_tax_amount,
                'transaction_count': transaction_count,
            }
        return rows

    def get_gl_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT
              to_char(date(account_move_line.date), 'DD-MM-YYYY') AS gldate,
              account_account.code,
              account_account.name AS account_name,
              account_move_line.name AS ref_name,
              account_journal.name AS journal,
              account_move.name AS entry_number,
              account_move.name AS SourceDocumentID,
              account_account_type.name,
              COALESCE(account_move_line.debit,0) AS debit, COALESCE(account_move_line.credit,0.00) AS credit,
              COALESCE(SUM(account_move_line.debit),0.00) - COALESCE(SUM(account_move_line.credit), 0.00) AS balance
            FROM
              public.account_move_line
              JOIN account_account on
                (account_account.id=account_move_line.account_id)
               JOIN account_account_type on
                (account_account_type.id=account_account.user_type_id)
              JOIN account_journal on
                (account_journal.id = account_move_line.journal_id)
              LEFT JOIN account_move on
                (account_move.id=account_move_line.move_id)
            WHERE account_account.company_id = %s AND account_move_line.date BETWEEN %s AND %s
            GROUP BY account_move_line.date,account_account.code,account_account.name,account_move_line.name,account_journal.name,
              account_move.name,account_move.name,account_account_type.name,account_move_line.debit,account_move_line.credit,account_move_line.move_id
            ORDER BY account_move_line.date,account_move_line.move_id""", (company_id, date_from, date_to))

        rows = self._cr.dictfetchall()
        return rows

    def get_gl_footer(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT 'GLDataEnd' AS GLDataEnd,ROUND(SUM(aml.debit),2) AS TotalDebit,
                            ROUND(SUM(aml.credit),2) AS TotalCredit,COUNT(aml.id) AS TransactionCountTotal,
                            'AED' AS GLTCurrency
                        FROM account_move_line aml
                        WHERE aml.company_id = %s AND aml.date BETWEEN %s AND %s""", (company_id, date_from, date_to))

        rows = self._cr.dictfetchall()
        return rows


# EXCISE FAF
class AccountExciseCSVExport(models.TransientModel):
    _name = 'csv.export_excise'
    _description = 'Generate Reports'

    data = fields.Binary('CSV', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    export_filename = fields.Char('Export CSV Filename', default='faf_report.csv', size=128)

    def action_manual_export_excise_entries(self):
        return self.env.ref('vat_trn.faf_excise_report_xlsx').report_action(self, data={}, config=False)

    def _get_header_compinfo(self):
        comp_info_start = ['CompInfoStart']
        return comp_info_start

    def _get_footer_compinfo(self):
        comp_info_end = ['CompInfoEnd']
        return comp_info_end

    def _get_header_journal_entries(self):
        if str(self.company_id.currency_id.name) == 'AED':
            trn_or_vat = 'TRN'
        else:
            trn_or_vat = 'VAT ID'
        file_headers = [
            'TaxablePersonNameEn',
            'TaxablePersonNameAr',
            trn_or_vat,
            'TaxAgencyName',
            'TAN',
            'TaxAgentName',
            'TAAN',
            'PeriodStart',
            'PeriodEnd',
            'FAFCreationDate',
            'ProductVersion',
            'FAFVersion',
        ]
        return file_headers

    def _get_header_vendor_bills(self):
        file_headers = [
            'SupplierName',
            'SupplierTIN/TRN',
            'InvoiceDate',
            'InvoiceNo',
            'PermitNo',
            'LineNo',
            'ProductDescription',
            'PurchaseValueAED',
            'ExciseTaxValueAED',
            'TaxCode',
            'FCY Code',
            'PurchaseFCY',
            'ExciseTaxFCY',
        ]
        return file_headers

    def _get_header_PurcDataStart(self):
        PurcDataStart = ['PurcDataStart']
        return PurcDataStart

    def _get_header_SuppDataStart(self):
        SuppDataStart = ['SuppDataStart']
        return SuppDataStart

    def _get_footer_vendor_bills(self):
        file_headers = [
            'PurcDataEnd',
            'PurchaseTotalAED',
            'VATTotalAED',
            'TransactionCountTotal',
        ]
        return file_headers

    def _get_header_invoices(self):
        file_headers = [
            'Customer Name',
            'CustomerTIN/TRN',
            'InvoiceDate',
            'InvoiceNo',
            'LineNo',
            'ProductDescription',
            'SupplyValueAED',
            'VATValueAED',
            'TaxCode',
            'Country',
            'FCYCode',
            'SupplyFCY',
            'VATFCY',
        ]
        return file_headers

    def _get_footer_invoices(self):
        file_headers = [
            'SuppDataEnd',
            'SupplyTotalAED',
            'VATTotalAED',
            'TransactionCountTotal',
        ]
        return file_headers

    def _get_header_GLDataStart(self):
        GLDataStart = ['GLDataStart']
        return GLDataStart

    def _get_header_gl(self):
        file_headers = [
            'TransactionDate',
            'AccountID',
            'AccountName',
            'TransactionDescription',
            'Name',
            'TransactionID',
            'SourceDocumentID',
            'SourceType',
            'Debit',
            'Credit',
            'Balance',
        ]
        return file_headers

    def _get_footer_gl(self):
        footers = ['GLDataEnd', 'TotalDebit', 'TotalCredit', 'TransactionCountTotal', 'GLTCurrency']
        return footers

    def get_data(self, result_type):
        date_from = self.date_from
        date_to = self.date_to
        company_id = self.company_id.id
        self._cr.execute("""
                SELECT
                  taxable_name_english as english_name,
                  company_name_arabic AS arabic_name,
                  vat_tax AS trn,
                  tax_agency_name AS tax_agency,
                  tan AS tan,
                  tax_agent_name AS tax_agent,
                  taan AS taan,
                  to_char(date %s, 'DD-MM-YYYY') AS date_from,
                  to_char(date %s, 'DD-MM-YYYY') AS date_to,
                  to_char(NOW(), 'DD-MM-YYYY') AS FAFCreationDate,
                  '1.0' AS ProductVersion,
                  'FAFv1.0.0' AS FAFVersion
                FROM
                  public.res_company
                WHERE res_company.id = %s
                """, (date_from, date_to, company_id))
        rows = self._cr.dictfetchall()
        return rows

    def get_vendor_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT partner.name AS partner,partner.vat AS vat,
                            ai.date_invoice AS date,ai.name AS invoice_number,ai.permit_no AS permit_number,
                            ail.sequence AS sequence_number,ail.name, ROUND(ail.price_subtotal*((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)),2) AS price_aed,ROUND((((ail.price_subtotal/100)*at.amount) * ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)) ),2)AS tax_amount,
                            at.tax_code,currency.name,ail.price_subtotal,((ail.price_subtotal/100)*at.amount) AS tax_amount
                        FROM account_move_line ail
                        JOIN account_move ai ON ai.id = ail.move_id
                        JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                        LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                        LEFT JOIN account_tax at ON at.id = ailt.tax_id
                        LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                        LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                        LEFT JOIN product_product pr ON pr.id = ail.product_id
                        WHERE ai.move_type = 'in_invoice' AND ai.state IN ('open','paid') AND at.tax_code = 'ET' AND ai.company_id = %s AND ai.date_invoice BETWEEN %s AND %s
                        GROUP BY partner.name,partner.vat,ai.date_invoice, ai.name,ai.permit_no,ail.sequence,ail.name, ail.price_subtotal,ai.id,ailt.invoice_line_id,at.id,
                        ailt.tax_id,ai.currency_id,currency.name,currency.id,cr_rate.rate
                        ORDER BY partner.name,ai.name,ai.id""", (company_id, date_from, date_to))
        rows2 = self._cr.dictfetchall()
        return rows2

    def get_vendor_footer_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT 'PurcDataEnd' AS PurcDataEnd,SUM(ROUND(ail.price_subtotal*
                                        ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)),2)) AS PurchaseTotalAED,
                                        ROUND(SUM((((ail.price_subtotal/100)*at.amount) * 
                                        ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)) )),2) AS VATTotalAED,COUNT(DISTINCT ai.id) AS TransactionCountTotal
                        FROM account_move_line ail
                        JOIN account_move ai ON ai.id = ail.move_id
                        JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                        LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                        LEFT JOIN account_tax at ON at.id = ailt.tax_id
                        LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                        LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                        LEFT JOIN product_product pr ON pr.id = ail.product_id
                        WHERE ai.move_type = 'in_invoice'  AND ai.state IN ('open','paid') AND ai.company_id = %s 
                        AND ai.date_invoice BETWEEN %s AND %s""",
                         (company_id, date_from, date_to))

        rows2 = self._cr.dictfetchall()
        return rows2

    def get_invoice_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT partner.name AS partner,partner.vat AS vat,
                            ai.date_invoice AS date,ai.name AS invoice_number,ail.sequence AS sequence_number,
                            ail.name,ROUND(ail.price_subtotal*((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)),2) AS price_aed,ROUND((((ail.price_subtotal/100)*at.amount) * ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)) ),2)AS tax_amount,at.tax_code AS tax_code,
                            country.name AS country,currency.name,ail.price_subtotal,((ail.price_subtotal/100)*at.amount) AS tax_amount
                        FROM account_move_line ail
                        JOIN account_move ai ON ai.id = ail.move_id
                        LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                        LEFT JOIN account_tax at ON at.id = ailt.tax_id
                        LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                        LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                        JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                        JOIN res_country country ON partner.country_id = country.id
                        LEFT JOIN product_product pr ON pr.id = ail.product_id
                        WHERE ai.move_type = 'out_invoice' AND ai.state IN ('open','paid') AND ai.company_id = %s AND ai.date_invoice BETWEEN %s AND %s
                        GROUP BY partner.name,partner.vat,ai.date_invoice, ai.name,ail.sequence,ail.name, ail.price_subtotal,ai.id,country.name,ailt.invoice_line_id,at.id,ailt.tax_id,
                        ai.currency_id,currency.name,currency.id,cr_rate.rate
                        ORDER BY partner.name,ai.name,ai.id""", (company_id, date_from, date_to))
        rows = self._cr.dictfetchall()
        return rows

    def get_invoices_footer_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT 'SuppDataEnd' AS SuppDataEnd,SUM(ROUND(ail.price_subtotal*((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)),2)) AS SupplyTotalAED,
                            ROUND(SUM((((ail.price_subtotal/100)*at.amount) * ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = 'AED'
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                          WHERE r.currency_id = c.id AND c.name = currency.name
                                       ORDER BY r.company_id, r.name DESC
                                          LIMIT 1)AS result)) )),2) AS VATTotalAED,COUNT(DISTINCT ai.id) AS TransactionCountTotal
                        FROM account_move_line ail
                        JOIN account_move ai ON ai.id = ail.move_id
                        JOIN res_partner partner ON ai.commercial_partner_id = partner.id
                        LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                        LEFT JOIN account_tax at ON at.id = ailt.tax_id
                        LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                        LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                        LEFT JOIN product_product pr ON pr.id = ail.product_id
                        WHERE ai.move_type = 'out_invoice'  AND ai.state IN ('open','paid') AND ai.company_id = %s AND ai.date_invoice 
                        BETWEEN %s AND %s""", (company_id, date_from, date_to))
        rows = self._cr.dictfetchall()
        return rows

    def get_gl_data(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT
                  account_move_line.date AS date,
                  account_account.code,
                  account_account.name,
                  account_move_line.name AS ref_name,
                  account_journal.name AS journal,
                  account_move.name AS entry_number,
                  account_move.name AS SourceDocumentID,
                  account_account_type.name,
                  COALESCE(account_move_line.debit,0) AS debit, COALESCE(account_move_line.credit,0.00) AS credit,
                  COALESCE(SUM(account_move_line.debit),0.00) - COALESCE(SUM(account_move_line.credit), 0.00) AS balance
                FROM
                   public.account_move_line
                  JOIN account_account on
                    (account_account.id=account_move_line.account_id)
                   JOIN account_account_type on
                    (account_account_type.id=account_account.user_type_id)
                  JOIN account_journal on
                    (account_journal.id = account_move_line.journal_id)
                  LEFT JOIN account_move on
                    (account_move.id=account_move_line.move_id)
                WHERE account_move_line.date BETWEEN %s AND %s
                GROUP BY account_move_line.date,account_account.code,account_account.name,account_move_line.name,account_journal.name,
                  account_move.name,account_move.name,account_account_type.name,account_move_line.debit,account_move_line.credit,account_move_line.move_id
                ORDER BY account_move_line.date,account_move_line.move_id""", (date_from, date_to))
        rows = self._cr.dictfetchall()
        return rows

    def get_gl_footer(self):
        company_id = self.company_id.id
        date_from = self.date_from
        date_to = self.date_to
        self._cr.execute("""SELECT 'GLDataEnd' AS GLDataEnd,ROUND(SUM(aml.debit),2) AS TotalDebit,
                            ROUND(SUM(aml.credit),2) AS TotalCredit,COUNT(aml.id) AS TransactionCountTotal,'AED' AS GLTCurrency
                        FROM account_move_line aml
                        WHERE aml.date BETWEEN %s AND %s""", (date_from, date_to))
        rows = self._cr.dictfetchall()
        return rows


class AccountVatReturns(models.Model):
    _name = 'vat.returns'
    _description = 'Generate Vat Return'

    # Form view to enter vat return report parameters
    data = fields.Binary('CSV', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    def _build_contexts(self, data):
        result = {}
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['company_id'] = data['form']['company_id'] or False
        return result

    def _print_report(self, data):
        return self.env.ref('vat_trn.vat_return').with_context(landscape=True).report_action(self, data=data)

    # @api.multi
    def check_report(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to','company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang') or 'en_US')
        return self._print_report(data)
