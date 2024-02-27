# -*- coding: utf-8 -*-
##############################################################################
#
#    Author Zaeem Solutions
#    Purpose: Backende logic for vat return file
##############################################################################

import datetime
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class VatReturnReport(models.AbstractModel):
    _name = 'report.vat_trn.vat_return_report'

# Fetch sales data based on each emirates
    def _get_standard_rated_supplies(self, data):
        company = data['form']['company_id']
        company_id = company[0]
        from_date = data['form']['date_from']
        start_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        to_date = data['form']['date_to']
        end_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        gcc_countries = ['Bahrain', 'Kuwait', 'Oman', 'Qatar', 'Saudi Arabia', 'United Arab Emirates']
        other_gcc_countries = ['Bahrain', 'Kuwait', 'Oman', 'Qatar', 'Saudi Arabia']
        result = {}
        self._cr.execute("""SELECT COALESCE(SUM(ROUND(ail.price_subtotal*((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                  WHERE r.currency_id = c.id AND c.name = 'AED'
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                  WHERE r.currency_id = c.id AND c.name = currency.name
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1)AS result)),2)),0.00) AS SupplyTotalAED,
                    COALESCE(ROUND(SUM((((ail.price_subtotal/100)*at.amount) * ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                  WHERE r.currency_id = c.id AND c.name = 'AED'
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                  WHERE r.currency_id = c.id AND c.name = currency.name
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1)AS result)) )),2),0.00) AS VATTotalAED,country.name AS ar_country,state.name AS ar_state,at.tax_code AS tax_code,ai.move_type AS ai_type
                FROM account_move_line ail
                JOIN account_move ai ON ai.id = ail.move_id
                JOIN res_partner partner ON ai.partner_id = partner.id
                JOIN res_country country ON country.id = partner.country_id
                JOIN res_country_state state ON state.id = partner.state_id
                LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                LEFT JOIN account_tax at ON at.id = ailt.tax_id
                LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                LEFT JOIN product_product pr ON pr.id = ail.product_id
                WHERE ai.move_type IN ('out_invoice','out_refund') AND ai.reverse_charges IS NOT TRUE AND ai.paid_customs_duty IS NOT TRUE AND ai.state IN ('open','paid') AND ai.company_id = %s AND ai.date_invoice BETWEEN %s AND %s 
                GROUP BY country.name,state.name,at.tax_code,ai.move_type""", (company_id, from_date, to_date))
        ar_state = self._cr.dictfetchall()
        supplytotalaed = 0
        vattotalaed = 0
        zrsupplytotalaed = 0
        for row in ar_state:
            fin_state = row.get('ar_state')
            fin_country = row.get('ar_country')
            tax_code = row.get('tax_code')
            ai_type = row.get('ai_type')

            if ai_type == 'out_invoice':
                if fin_state == 'Dubai' and tax_code == 'SR':
                    dubai_amount = row.get('supplytotalaed')
                    supplytotalaed += dubai_amount
                    result.update({'dubai_amount':dubai_amount})
                    dubai_vat_amount = row.get('vattotalaed')
                    vattotalaed += dubai_vat_amount
                    result.update({'dubai_vat_amount': dubai_vat_amount})
                elif fin_state == 'Ajman' and tax_code == 'SR':
                    ajman_amount = row.get('supplytotalaed')
                    supplytotalaed += ajman_amount
                    result.update({'ajman_amount':ajman_amount})
                    ajman_vat_amount = row.get('vattotalaed')
                    vattotalaed += ajman_vat_amount
                    result.update({'ajman_vat_amount':ajman_vat_amount})
                elif fin_state == 'Abu Dhabi' and tax_code == 'SR':
                    abudhabi_amount = row.get('supplytotalaed')
                    supplytotalaed += abudhabi_amount
                    result.update({'abudhabi_amount':abudhabi_amount})
                    abudhabi_vat_amount = row.get('vattotalaed')
                    vattotalaed += abudhabi_vat_amount
                    result.update({'abudhabi_vat_amount':abudhabi_vat_amount})
                elif fin_state == 'Fujairah' and tax_code == 'SR':
                    fujairah_amount = row.get('supplytotalaed')
                    supplytotalaed += fujairah_amount
                    result.update({'fujairah_amount':fujairah_amount})
                    fujairah_vat_amount = row.get('vattotalaed')
                    vattotalaed += fujairah_vat_amount
                    result.update({'fujairah_vat_amount':fujairah_vat_amount})
                elif fin_state == 'Ras al-Khaimah' and tax_code == 'SR':
                    rak_amount = row.get('supplytotalaed')
                    supplytotalaed += rak_amount
                    result.update({'rak_amount':rak_amount})
                    rak_vat_amount = row.get('vattotalaed')
                    vattotalaed += rak_vat_amount
                    result.update({'rak_vat_amount':rak_vat_amount})
                elif fin_state == 'Sharjah' and tax_code == 'SR':
                    sharjah_amount = row.get('supplytotalaed')
                    supplytotalaed += sharjah_amount
                    result.update({'sharjah_amount':sharjah_amount})
                    sharjah_vat_amount = row.get('vattotalaed')
                    vattotalaed += sharjah_vat_amount
                    result.update({'sharjah_vat_amount':sharjah_vat_amount})
                elif fin_state == 'Umm al-Quwain' and tax_code == 'SR':
                    uaq_amount = row.get('supplytotalaed')
                    supplytotalaed += uaq_amount
                    result.update({'uaq_amount':uaq_amount})
                    uaq_vat_amount = row.get('vattotalaed')
                    vattotalaed += uaq_vat_amount
                    result.update({'uaq_vat_amount':uaq_vat_amount})
                if tax_code == 'EX':
                    exempt_supply = row.get('supplytotalaed')
                    supplytotalaed += exempt_supply
                    result.update({'exempt_supply':exempt_supply})
                if fin_country not in gcc_countries and tax_code == 'ZR':
                    zrsupplyaed = row.get('supplytotalaed')
                    supplytotalaed += zrsupplyaed
                    result.update({'zrsupplyaed':zrsupplyaed})
                elif fin_country in other_gcc_countries:
                    gcc_supply = row.get('supplytotalaed')
                    supplytotalaed += gcc_supply
                    result.update({'gcc_supply':gcc_supply})
            elif ai_type == 'out_refund':
                if fin_state == 'Dubai' and tax_code == 'SR':
                    dubai_amount_refund = row.get('supplytotalaed')
                    supplytotalaed -= dubai_amount_refund
                    result.update({'dubai_amount_refund':dubai_amount_refund})
                    dubai_vat_amount_refund = row.get('vattotalaed')
                    vattotalaed -= dubai_vat_amount_refund
                    result.update({'dubai_vat_amount_refund':dubai_vat_amount_refund})
                elif fin_state == 'Ajman' and tax_code == 'SR':
                    ajman_amount_refund = row.get('supplytotalaed')
                    supplytotalaed -= ajman_amount_refund
                    result.update({'ajman_amount_refund':ajman_amount_refund})
                    ajman_vat_amount_refund = row.get('vattotalaed')
                    vattotalaed -= ajman_vat_amount_refund
                    result.update({'ajman_vat_amount_refund':ajman_vat_amount_refund})
                elif fin_state == 'Abu Dhabi' and tax_code == 'SR':
                    abudhabi_amount_refund = row.get('supplytotalaed')
                    supplytotalaed -= abudhabi_amount_refund
                    result.update({'abudhabi_amount_refund':abudhabi_amount_refund})
                    abudhabi_vat_amount_refund = row.get('vattotalaed')
                    vattotalaed -= abudhabi_vat_amount_refund
                    result.update({'abudhabi_vat_amount_refund':abudhabi_vat_amount_refund})
                elif fin_state == 'Fujairah' and tax_code == 'SR':
                    fujairah_amount_refund = row.get('supplytotalaed')
                    supplytotalaed -= fujairah_amount_refund
                    result.update({'fujairah_amount_refund':fujairah_amount_refund})
                    fujairah_vat_amount_refund = row.get('vattotalaed')
                    vattotalaed -= fujairah_vat_amount_refund
                    result.update({'fujairah_vat_amount_refund':fujairah_vat_amount_refund})
                elif fin_state == 'Ras al-Khaimah' and tax_code == 'SR':
                    rak_amount_refund = row.get('supplytotalaed')
                    supplytotalaed -= rak_amount
                    result.update({'rak_amount_refund':rak_amount_refund})
                    rak_vat_amount_refund = row.get('vattotalaed')
                    vattotalaed -= rak_vat_amount_refund
                    result.update({'rak_vat_amount_refund':rak_vat_amount_refund})
                elif fin_state == 'Sharjah' and tax_code == 'SR':
                    sharjah_amount_refund = row.get('supplytotalaed')
                    supplytotalaed -= sharjah_amount_refund
                    result.update({'sharjah_amount_refund':sharjah_amount_refund})
                    sharjah_vat_amount_refund = row.get('vattotalaed')
                    vattotalaed -= sharjah_vat_amount_refund
                    result.update({'sharjah_vat_amount_refund':sharjah_vat_amount_refund})
                elif fin_state == 'Umm al-Quwain' and tax_code == 'SR':
                    uaq_amount_refund = row.get('supplytotalaed')
                    supplytotalaed -= uaq_amount_refund
                    result.update({'uaq_amount_refund':uaq_amount_refund})
                    uaq_vat_amount_refund = row.get('vattotalaed')
                    vattotalaed -= uaq_vat_amount_refund
                    result.update({'uaq_vat_amount_refund':uaq_vat_amount_refund})

                if tax_code == 'EX':
                    exempt_supply = row.get('supplytotalaed')
                    supplytotalaed -= exempt_supply
                    result.update({'exempt_supply':exempt_supply})

                if fin_country not in gcc_countries and tax_code == 'ZR':
                    zrsupplyaed = row.get('supplytotalaed')
                    supplytotalaed -= zrsupplyaed
                    result.update({'zrsupplyaed': zrsupplyaed})

                elif fin_country in other_gcc_countries:
                    gcc_supply = row.get('supplytotalaed')
                    supplytotalaed -= gcc_supply
                    result.update({'gcc_supply': gcc_supply})
        result.update({'supplytotalaed': supplytotalaed})
        result.update({'vattotalaed': vattotalaed})

        return result

# Fetch cancelled invoice data based on each emirates
    def _get_tax_credits(self, data):
        company = data['form']['company_id']
        company_id = company[0]
        from_date = data['form']['date_from']
        start_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        to_date = data['form']['date_to']
        end_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        gcc_countries = ['Bahrain', 'Kuwait', 'Oman', 'Qatar', 'Saudi Arabia', 'United Arab Emirates']
        other_gcc_countries = ['Bahrain', 'Kuwait', 'Oman', 'Qatar', 'Saudi Arabia']
        result = {}
        self._cr.execute("""SELECT
                    ai.move_type AS ai_type,
                    state.name AS ar_state,
                    SUM(mtv.new_value_monetary) AS vattotalaed
                    FROM
                    public.mail_tracking_value mtv
                    JOIN public.mail_message mm ON mm.id = mtv.mail_message_id
                    JOIN account_move ai ON ai.id = mm.res_id
                    JOIN res_partner partner ON ai.partner_id = partner.id
                    JOIN res_country country ON country.id = partner.country_id
                    JOIN res_country_state state ON state.id = partner.state_id
                    WHERE 
                    ai.move_type IN ('out_invoice','out_refund') and
                    ai.company_id = %s and
                    mtv.field_desc = 'VAT' and mtv.new_value_monetary > 0 and
                    mtv.mail_message_id  IN ( SELECT mtvv.mail_message_id  from public.mail_tracking_value mtvv where 
                    to_date(to_char(mtvv.old_value_datetime, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text)  < %s and mtvv.mail_message_id IN 
                    (SELECT mtvvv.mail_message_id  from public.mail_tracking_value mtvvv WHERE mtvvv.new_value_char ='Cancelled' and mtvvv.old_value_char = 'Open'
                    and mtv.write_date::date BETWEEN %s AND %s) 
                    ORDER by mtvv.write_date)
                    GROUP BY state.name,ai.move_type""", (company_id, from_date, from_date, to_date))
        ar_state = self._cr.dictfetchall()
        supplytotalaed = 0
        vattotalaed = 0
        zrsupplytotalaed = 0
        for row in ar_state:
            fin_state = row.get('ar_state')
            #fin_country = row.get('ar_country')
            #tax_code = row.get('tax_code')
            ai_type = row.get('ai_type')

            if ai_type == 'out_invoice':
                if fin_state == 'Dubai':
                    dubai_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed += dubai_vat_amount_credit
                    result.update({'dubai_vat_amount_credit':dubai_vat_amount_credit})

                elif(fin_state == 'Ajman'):
                    ajman_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed += ajman_vat_amount_credit
                    result.update({'ajman_vat_amount_credit':ajman_vat_amount_credit})

                elif(fin_state == 'Abu Dhabi'):
                    abudhabi_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed += abudhabi_vat_amount_credit
                    result.update({'abudhabi_vat_amount_credit':abudhabi_vat_amount_credit})

                elif(fin_state == 'Fujairah'):
                    fujairah_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed += fujairah_vat_amount_credit
                    result.update({'fujairah_vat_amount_credit':fujairah_vat_amount_credit})

                elif(fin_state == 'Ras al-Khaimah'):
                    rak_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed += rak_vat_amount_credit
                    result.update({'rak_vat_amount_credit':rak_vat_amount_credit})

                elif(fin_state == 'Sharjah'):
                    sharjah_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed += sharjah_vat_amount_credit
                    result.update({'sharjah_vat_amount_credit':sharjah_vat_amount_credit})

                elif(fin_state == 'Umm al-Quwain'):
                    uaq_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed += uaq_vat_amount_credit
                    result.update({'uaq_vat_amount_credit':uaq_vat_amount_credit})

            elif(ai_type=='out_refund'):
                if(fin_state == 'Dubai'):
                    dubai_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed -= dubai_vat_amount_credit
                    result.update({'dubai_vat_amount_credit':dubai_vat_amount_credit})

                elif(fin_state == 'Ajman'):
                    ajman_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed -= ajman_vat_amount_credit
                    result.update({'ajman_vat_amount_credit':ajman_vat_amount_credit})

                elif(fin_state == 'Abu Dhabi'):
                    abudhabi_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed -= abudhabi_vat_amount_credit
                    result.update({'abudhabi_vat_amount_credit':abudhabi_vat_amount_credit})

                elif(fin_state == 'Fujairah'):
                    fujairah_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed -= fujairah_vat_amount_credit
                    result.update({'fujairah_vat_amount_credit':fujairah_vat_amount_credit})

                elif(fin_state == 'Ras al-Khaimah'):
                    rak_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed -= rak_vat_amount_credit
                    result.update({'rak_vat_amount_credit':rak_vat_amount_credit})

                elif(fin_state == 'Sharjah'):
                    sharjah_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed -= sharjah_vat_amount_credit
                    result.update({'sharjah_vat_amount_credit':sharjah_vat_amount_credit})

                elif(fin_state == 'Umm al-Quwain'):
                    uaq_vat_amount_credit = row.get('vattotalaed')
                    vattotalaed -= uaq_vat_amount_credit
                    result.update({'uaq_vat_amount_credit':uaq_vat_amount_credit})
        result.update({'vattotalaed': vattotalaed})

        return result

    def _get_standard_rated_purchases(self, data):
        # Fetch vendor bills data
        company = data['form']['company_id']
        company_id = company[0]
        from_date = data['form']['date_from']
        to_date = data['form']['date_to']

        ret_field = 0
        result = {}
        comp = self.env['res.company'].browse(company_id)
        companies = self.env['res.company'].search([('currency_id', '=', comp.currency_id.id)])
        self._cr.execute("""SELECT SUM(ROUND(ail.price_subtotal,2)) AS PurchaseTotalAed,
                            COALESCE(ROUND(SUM((ail.price_subtotal/100)*at.amount),2),0) AS PurchaseVatTotalAed,
                            ai.move_type AS ai_type
                            FROM account_move_line ail
                            JOIN account_move ai ON ai.id = ail.move_id
                            JOIN res_partner partner ON ai.partner_id = partner.id
                            JOIN res_country_state state ON state.id = partner.state_id
                            LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                            LEFT JOIN account_tax at ON at.id = ailt.tax_id
                            LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                            LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                            LEFT JOIN product_product pr ON pr.id = ail.product_id
                            WHERE ai.move_type IN ('in_invoice','in_refund') 
                            AND ai.reverse_charges IS NOT TRUE 
                            AND ai.paid_customs_duty IS NOT TRUE 
                            AND ai.state IN ('open','paid') 
                            AND ai.company_id IN %s 
                            AND ai.date_invoice BETWEEN %s AND %s 
                            AND at.amount > 0.0
                            GROUP BY ai.name, ai.move_type, ai.amount_tax""", (tuple(companies.ids), from_date, to_date))
        ar_state = self._cr.dictfetchall()
        purchaseTotalAed = 0
        purchaseVatTotalAed = 0
        zrsupplytotalaed = 0
        purchase_amount = 0
        purchase_vat_amount = 0
        for row in ar_state:
            tax_code = row.get('tax_code')
            ai_type = row.get('ai_type')
            if tax_code == 'SR':
                if ai_type == 'in_invoice':
                    purchase_amount_line = row.get('purchasetotalaed')
                    purchase_vat_amount_line = row.get('purchasevattotalaed')
                    purchase_amount += purchase_amount_line
                    purchase_vat_amount += purchase_vat_amount_line
                    purchaseTotalAed += purchase_amount_line
                    purchaseVatTotalAed += purchase_vat_amount_line
                if ai_type == 'in_refund':
                    purchase_refund_amount_line = row.get('purchasetotalaed',0)
                    purchase_refund_vat_amount_line = row.get('purchasevattotalaed',0)
                    purchase_amount -= purchase_refund_amount_line
                    purchase_vat_amount -= purchase_refund_vat_amount_line
                    purchaseTotalAed -= purchase_refund_amount_line
                    purchaseVatTotalAed -= purchase_refund_vat_amount_line

                result.update({'purchase_amount': purchase_amount})
                result.update({'purchase_vat_amount': purchase_vat_amount})

        # petty cash vat add
        self._cr.execute("""SELECT 
                            SUM(ROUND(COALESCE(account_move.amount_untaxed, 0),2)) AS PurchaseTotalAed,
                            COALESCE(SUM(ROUND(account_move.amount_tax,2)),0) AS PurchaseVatTotalAed
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
                            LEFT JOIN res_partner partner ON partner.id = account_move.partner_id
                            LEFT JOIN account_tax ON account_tax.id = account_move_line.tax_line_id
                            LEFT JOIN res_currency  ON res_currency.id = account_move.currency_id
                            WHERE account_account.company_id IN %s 
                            AND account_move_line.date BETWEEN %s AND %s
                            AND account_journal.type = 'cash' AND account_account.name = 'Taxes Paid'""",
                         (tuple(companies.ids), from_date, to_date))
        ar_petty_state = self._cr.dictfetchall()
        purchaseTotalAedPetty = 0
        purchaseVatTotalAedPetty = 0
        zrsupplytotalaed = 0
        purchase_amount_petty = result.get('purchase_amount')
        purchase_vat_amount_petty = result.get('purchase_vat_amount')
        if purchase_amount_petty is None or purchase_vat_amount_petty is None:
            purchase_amount_petty = purchase_vat_amount_petty = 0.0
        for row in ar_petty_state:
            # fin_state = row.get('ar_state')
            # tax_code = row.get('tax_code')
            # ai_type = row.get('ai_type')
            # if tax_code == 'SR':
            purchase_amount_line_petty = row.get('purchasetotalaed')
            purchase_vat_amount_line_petty = row.get('purchasevattotalaed')
            if purchase_amount_line_petty is None or purchase_vat_amount_line_petty is None:
                purchase_amount_line_petty = purchase_vat_amount_line_petty = 0.0
            purchase_amount_petty += purchase_amount_line_petty if purchase_amount_line_petty else 0.0
            purchase_vat_amount_petty += purchase_vat_amount_line_petty

            result.update({'purchase_amount': purchase_amount_petty})
            result.update({'purchase_vat_amount': purchase_vat_amount_petty})

        result.update({'purchaseTotalAed': purchase_amount_petty})
        result.update({'purchaseVatTotalAed': purchase_vat_amount_petty})
        return result

    # fetch all the purchase tax credits
    def _get_purchase_vat_credit(self,data):
        # Fetch vendor bills data
        company = data['form']['company_id']
        company_id = company[0]
        from_date = data['form']['date_from']
        start_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        to_date = data['form']['date_to']
        end_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime("%d/%m/%Y")

        ret_field = 0


        result = {}
        self._cr.execute("""SELECT
                    ai.move_type AS ai_type,
                    SUM(mtv.new_value_monetary) AS purchasevattotalaed
                    FROM
                    public.mail_tracking_value mtv
                    JOIN public.mail_message mm ON mm.id = mtv.mail_message_id
                    JOIN account_move ai ON ai.id = mm.res_id
                    JOIN res_partner partner ON ai.partner_id = partner.id
                    JOIN res_country country ON country.id = partner.country_id
                    JOIN res_country_state state ON state.id = partner.state_id

                    WHERE 
                    ai.move_type IN ('in_invoice','in_refund') and
                    ai.company_id = %s and
                    mtv.field_desc = 'VAT' and mtv.new_value_monetary > 0 and
                    mtv.mail_message_id  IN ( SELECT mtvv.mail_message_id  from public.mail_tracking_value mtvv where 
                    to_date(to_char(mtvv.old_value_datetime, 'YYYY-MM-DD'::text), 'YYYY-MM-DD'::text)  < %s and mtvv.mail_message_id IN 
                    (SELECT mtvvv.mail_message_id  from public.mail_tracking_value mtvvv WHERE mtvvv.new_value_char ='Cancelled' and mtvvv.old_value_char = 'Open'
                    and mtv.write_date::date BETWEEN %s AND %s) 
                    ORDER by mtvv.write_date)

                    GROUP BY ai.move_type""", (company_id, from_date, from_date, to_date))
        ar_state = self._cr.dictfetchall()
        purchaseTotalAed = 0
        purchaseVatTotalAed = 0
        zrsupplytotalaed = 0
        purchase_amount = 0
        purchase_vat_credit = 0
        for row in ar_state:
           # fin_state = row.get('ar_state')
            tax_code = row.get('tax_code')
            ai_type = row.get('ai_type')
            if(tax_code == 'SR'):

              if(ai_type=='in_invoice'):
                  purchase_vat_amount_line = row.get('purchasevattotalaed',0)
                  purchase_vat_credit += purchase_vat_amount_line
              elif(ai_type=='in_refund'):
                  purchase_vat_amount_line = row.get('purchasevattotalaed',0)
                  purchase_vat_credit -= purchase_vat_amount_line

        result.update({'purchase_vat_credit':purchase_vat_credit})

        return result

    def _get_reverse_charge_items(self,data):
        #Fetch vendor bills with reverse charge
        company = data['form']['company_id']
        company_id = company[0]
        from_date = data['form']['date_from']
        start_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        to_date = data['form']['date_to']
        end_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime("%d/%m/%Y")

        ret_field = 0
        #count = self._cr.rowcount
       # if(field == "VATTotalAED"):
        #    ret_field = 1

        result = {}
        self._cr.execute("""SELECT COALESCE(SUM(ROUND(price_total,2)),0.00) AS PurchaseTotalAed,
                    COALESCE(ROUND(SUM(((ail.price_total/100)*at.amount)),2),0.00) AS PurchaseVatTotalAed,ai.move_type AS inv_type
                FROM account_move_line ail
                JOIN account_move ai ON ai.id = ail.move_id
                JOIN res_partner partner ON ai.partner_id = partner.id
                JOIN res_country_state state ON state.id = partner.state_id
                LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                LEFT JOIN account_tax at ON at.id = ailt.tax_id
                LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                LEFT JOIN product_product pr ON pr.id = ail.product_id
                WHERE ai.reverse_charges AND ai.state IN ('open','paid') AND ai.company_id = %s AND ai.date_invoice BETWEEN %s AND %s 
                GROUP BY ai.move_type""", (company_id, from_date, to_date))
        ar_state = self._cr.dictfetchall()
        for row in ar_state:
           # fin_state = row.get('ar_state')
            inv_type = row.get('inv_type')
            if (inv_type == 'in_invoice'):
                vendor_reverse_charge_amount = row.get('purchasetotalaed')
                result.update({'vendor_reverse_charge_amount':vendor_reverse_charge_amount})
                vendor_reverse_charge_value = row.get('purchasevattotalaed')
                result.update({'vendor_reverse_charge_value':vendor_reverse_charge_value})
            elif(inv_type=="in_refund"):
                vendor_reverse_charge_refund_amount = row.get('purchasetotalaed')
                result.update({'vendor_reverse_charge_refund_amount':-vendor_reverse_charge_refund_amount})
                vendor_reverse_charge_refund_value = row.get('purchasevattotalaed')
                result.update({'vendor_reverse_charge_refund_value':-vendor_reverse_charge_refund_value})

        return result 

    def _get_customs_duty_items(self,data):
        #Fetch customs duty
        company = data['form']['company_id']
        company_id = company[0]
        from_date = data['form']['date_from']
        start_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        to_date = data['form']['date_to']
        end_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime("%d/%m/%Y")

        ret_field = 0
        #count = self._cr.rowcount
       # if(field == "VATTotalAED"):
        #    ret_field = 1

        result = {}
        self._cr.execute("""SELECT COALESCE(SUM(ROUND(ail.price_subtotal*((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                  WHERE r.currency_id = c.id AND c.name = 'AED'
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                  WHERE r.currency_id = c.id AND c.name = currency.name
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1)AS result)),2)),0.00) AS PurchaseTotalAed,
                    COALESCE(ROUND(SUM((((ail.price_subtotal/100)*at.amount) * ((SELECT (SELECT r.rate FROM res_currency_rate r ,res_currency c
                                  WHERE r.currency_id = c.id AND c.name = 'AED'
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1) /(SELECT r.rate FROM res_currency_rate r ,res_currency c
                                  WHERE r.currency_id = c.id AND c.name = currency.name
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1)AS result)) )),2),0.00) AS PurchaseVatTotalAed
                FROM account_move_line ail
                JOIN account_move ai ON ai.id = ail.move_id
                JOIN res_partner partner ON ai.partner_id = partner.id
                JOIN res_country_state state ON state.id = partner.state_id
                LEFT JOIN account_invoice_line_tax ailt ON ailt.invoice_line_id = ail.id
                LEFT JOIN account_tax at ON at.id = ailt.tax_id
                LEFT JOIN res_currency currency ON currency.id = ai.currency_id
                LEFT JOIN res_currency_rate cr_rate ON cr_rate.id = currency.id 
                LEFT JOIN product_product pr ON pr.id = ail.product_id
                WHERE ai.paid_customs_duty AND ai.state IN ('open','paid') AND ai.company_id = %s AND ai.date_invoice BETWEEN %s AND %s
                """,(company_id,from_date,to_date))
        ar_state = self._cr.dictfetchall()
        for row in ar_state:
           # fin_state = row.get('ar_state')
            paid_customs_duty_amount = row.get('purchasetotalaed')
            result.update({'paid_customs_duty_amount':paid_customs_duty_amount})
            paid_customs_duty_value = row.get('purchasevattotalaed')
            result.update({'paid_customs_duty_value':paid_customs_duty_value})
        return result   

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))

        # target_move = data['form'].get('target_move', 'all')
        # sort_selection = data['form'].get('sort_selection', 'date')
        sales_val = self._get_standard_rated_supplies(data)
        tax_credits = self._get_tax_credits(data)
        expense_val = self._get_standard_rated_purchases(data)
        purchase_vat_credit = self._get_purchase_vat_credit(data)
        reverse_val = self._get_reverse_charge_items(data)
        customs_val = self._get_customs_duty_items(data)
        from_date = data['form']['date_from']
        start_date = datetime.datetime.strptime(from_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        to_date = data['form']['date_to']
        end_date = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        tax_year = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime("%B-%Y")
        return_period_ref = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime("%m-%Y")
        return_period = start_date + ' - ' + end_date

        total_supplies_amount = 0
        total_supplies_vat_amount = 0
        total_vat_credit = 0

        if sales_val.get('supplytotalaed'):
            total_supplies_amount += sales_val.get('supplytotalaed')

        if reverse_val.get('vendor_reverse_charge_amount'):
            total_supplies_amount += reverse_val.get('vendor_reverse_charge_amount')

        if customs_val.get('paid_customs_duty_amount'):
            total_supplies_amount += customs_val.get('paid_customs_duty_amount')

        if sales_val.get('vattotalaed'):
            total_supplies_vat_amount += sales_val.get('vattotalaed')

        if tax_credits.get('vattotalaed'):
            total_vat_credit += tax_credits.get('vattotalaed')
            msg1 = ("This is my debug message tax_credits! %s",tax_credits)
            _logger.error(msg1)

        if reverse_val.get('vendor_reverse_charge_value'):
            total_supplies_vat_amount += reverse_val.get('vendor_reverse_charge_value')

        if customs_val.get('paid_customs_duty_value'):
            total_supplies_vat_amount += customs_val.get('paid_customs_duty_value')

        total_expense_amount = 0
        total_expense_vat_amount = 0
        purchase_vat_credit_amount = 0

        if expense_val.get('purchaseTotalAed'):
            total_expense_amount += expense_val.get('purchaseTotalAed')

        if purchase_vat_credit.get('purchase_vat_credit'):
            purchase_vat_credit_amount += purchase_vat_credit.get('purchase_vat_credit')

        if reverse_val.get('vendor_reverse_charge_amount'):
            total_expense_amount += reverse_val.get('vendor_reverse_charge_amount')

        if expense_val.get('purchaseVatTotalAed'):
            total_expense_vat_amount += expense_val.get('purchaseVatTotalAed')

        if reverse_val.get('vendor_reverse_charge_value'):
            total_expense_vat_amount += reverse_val.get('vendor_reverse_charge_value')

        res = {}
        # for journal in data['form']['journal_ids']:
        # res[journal] = self.with_context(data['form'].get('used_context', {})).lines(
        # target_move, journal, sort_selection, data)
        docargs = {
            # 'doc_ids': data['form']['journal_ids'],
            # 'doc_model': self.env['account.journal'],
            'data': data,
            'return_date_start': start_date,
            'return_date_end': end_date,
            'return_period': return_period,
            'return_period_ref': return_period_ref,
            'tax_year': tax_year,
            'value': sales_val,
            'tax_credits': tax_credits,
            'expense_val': expense_val,
            'reverse_val': reverse_val,
            'customs_val': customs_val,
            'total_expense_amount': total_expense_amount,
            'purchase_vat_credit_amount': purchase_vat_credit_amount,
            'total_expense_vat_amount': total_expense_vat_amount,
            'total_supplies_amount': total_supplies_amount,
            'total_supplies_vat_amount': total_supplies_vat_amount,
            'total_vat_credit': total_vat_credit,
            # 'get_standard_rated_supplies_total': self._get_standard_rated_supplies_total,
            # 'get_taxes': self._get_taxes,
        }
        # return self.env['report'].render('vat_trn.vat_return_report', docargs)
        return docargs