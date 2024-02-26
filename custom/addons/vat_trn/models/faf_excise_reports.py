from odoo import models


class CSVExportExciseXLSX(models.AbstractModel):
    _name = 'report.vat_trn.faf_excise_report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, objs):
        rows = objs.get_data("journal_entries")
        CompInfoStart = objs._get_header_compinfo()
        file_headers = objs._get_header_journal_entries()
        CompInfoEnd = objs._get_footer_compinfo()
        PurcDataStart = objs._get_header_PurcDataStart()
        header_vendor_bills = objs._get_header_vendor_bills()
        vendor_bills = objs.get_vendor_data()
        footer_vendor_bills = objs._get_footer_vendor_bills()
        vendor_bills_footer = objs.get_vendor_footer_data()
        SuppDataStart = objs._get_header_SuppDataStart()
        header_invoices = objs._get_header_invoices()
        invoices = objs.get_invoice_data()
        footer_invoices = objs._get_footer_invoices()
        invoices_footer = objs.get_invoices_footer_data()
        GLDataStart = objs._get_header_GLDataStart()
        header_gl = objs._get_header_gl()
        gl_data = objs.get_gl_data()
        footer_gl = objs._get_footer_gl()
        gl_footer = objs.get_gl_footer()

        # workbook starts here
        worksheet = workbook.add_worksheet('FAF Excise Report')
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 15)
        worksheet.set_column('I:I', 15)
        worksheet.set_column('J:J', 15)
        worksheet.set_column('K:K', 15)
        worksheet.set_column('L:L', 15)
        worksheet.set_column('M:M', 15)
        worksheet.write('A1', CompInfoStart[0])
        col = 0
        for i in rows:
            rows2 = list(i)
        for i in range(len(file_headers)):
            row = 1
            worksheet.write(row, col, file_headers[i])
            row = 2
            worksheet.write(row, col, rows2[i])
            col = col + 1
        row = row + 1
        col = 0
        worksheet.write(row, col, CompInfoEnd[0])
        worksheet.write(row + 1, col, PurcDataStart[0])
        row = row + 2
        col = 0
        for i in range(len(header_vendor_bills)):
            worksheet.write(row, col, header_vendor_bills[i])
            col = col + 1
        for i in vendor_bills:
            if not i['tax_amount']:
                i['tax_amount'] = 0
            if i['ai_type'] == "in_refund":
                i['price_aed'] = -1 * i['price_aed']
                i['AEDFCY'] = -1 * i['AEDFCY']
                i['price_subtotal'] = -1 * i['price_subtotal']
                i['tax_amount'] = -1 * i['tax_amount']

            row = row + 1
            col = 0
            worksheet.write(row, col, i['partner'])
            worksheet.write(row, col+1, i['vat'])
            worksheet.write(row, col+2, i['billdate'])
            worksheet.write(row, col+3, i['invoice_number'])
            worksheet.write(row, col+4, i['permit_number'])
            worksheet.write(row, col+5, i['sequence_number'])
            worksheet.write(row, col+6, i['ail_name'])
            worksheet.write(row, col+7, i['price_aed'])
            worksheet.write(row, col+8, i['tax_amount'])
            worksheet.write(row, col+9, i['tax_code'])
            worksheet.write(row, col+10, i['currency_name'])
            worksheet.write(row, col+11, i['price_subtotal'])
            worksheet.write(row, col+12, i['AEDFCY'])

        row = row + 2
        col = 0
        for i in range(len(footer_vendor_bills)):
            worksheet.write(row, col, footer_vendor_bills[i])
            col = col + 1

        row = row + 1
        col = 0
        worksheet.write(row, col, vendor_bills_footer[0]['purcdataend'])
        worksheet.write(row, col + 1, vendor_bills_footer[0]['purchasetotalaed'])
        worksheet.write(row, col + 2, vendor_bills_footer[0]['vattotalaed'])
        worksheet.write(row, col + 3, vendor_bills_footer[0]['transactioncounttotal'])

        row = row + 1
        col = 0
        worksheet.write(row, col, SuppDataStart[0])
        row = row + 1
        col = 0
        for i in range(len(header_invoices)):
            worksheet.write(row, col, header_invoices[i])
            col = col + 1

        for i in invoices:
            # Checking the tax_amount and tax_amount_aed is none to avoid none value
            if i['tax_amount_aed'] is None:
                i['tax_amount_aed'] = 0.0
            if i['tax_amount'] is None:
                i['tax_amount'] = 0.0
            if i['ai_type'] == "out_refund":
                i['price_aed'] = -1 * i['price_aed']
                i['tax_amount_aed'] = -1 * i['tax_amount_aed']
                i['price_subtotal'] = -1 * i['price_subtotal']
                i['tax_amount'] = -1 * i['tax_amount']

            row = row + 1
            col = 0
            worksheet.write(row, col, i['partner'])
            worksheet.write(row, col+1, i['vat'])
            worksheet.write(row, col+2, i['invoicedate'])
            worksheet.write(row, col+3, i['invoice_number'])
            worksheet.write(row, col+4, i['sequence_number'])
            worksheet.write(row, col+5, i['ail_name'])
            worksheet.write(row, col+6, i['price_aed'])
            worksheet.write(row, col+7, i['tax_amount_aed'])
            worksheet.write(row, col+8, i['tax_code'])
            worksheet.write(row, col+9, i['country'])
            worksheet.write(row, col+10, i['currency'])
            worksheet.write(row, col+11, i['price_subtotal'])
            worksheet.write(row, col+12, i['tax_amount'])

        row = row + 2
        col = 0
        for i in range(len(footer_invoices)):
            worksheet.write(row, col, footer_invoices[i])
            col = col + 1

        row = row + 1
        col = 0
        worksheet.write(row, col, invoices_footer[0]['suppdataend'])
        worksheet.write(row, col + 1, invoices_footer[0]['supplytotalaed'])
        worksheet.write(row, col + 2, invoices_footer[0]['vattotalaed'])
        worksheet.write(row, col + 3, invoices_footer[0]['transactioncounttotal'])

        col = 0
        worksheet.write(row + 1, col, GLDataStart[0])
        row = row + 2
        col = 0
        for i in range(len(header_gl)):
            worksheet.write(row, col, header_gl[i])
            col = col + 1

        for i in gl_data:
            row = row + 1
            col = 0
            worksheet.write(row, col, i['date'])
            worksheet.write(row, col+1, i['code'])
            worksheet.write(row, col+2, i['name'])
            worksheet.write(row, col+3, i['ref_name'])
            worksheet.write(row, col+4, i['journal'])
            worksheet.write(row, col+5, i['entry_number'])
            worksheet.write(row, col+6, i['sourcedocumentid'])
            worksheet.write(row, col+7, i['name'])
            worksheet.write(row, col+8, i['debit'])
            worksheet.write(row, col+9, i['credit'])
            worksheet.write(row, col+10, i['balance'])

        row = row + 1
        col = 0
        for i in range(len(footer_gl)):
            worksheet.write(row, col, footer_gl[i])
            col = col + 1

        row = row + 1
        col = 0
        worksheet.write(row, col, gl_footer[0]['gldataend'])
        worksheet.write(row, col + 1, gl_footer[0]['totaldebit'])
        worksheet.write(row, col + 2, gl_footer[0]['totalcredit'])
        worksheet.write(row, col + 3, gl_footer[0]['transactioncounttotal'])
        worksheet.write(row, col + 4, gl_footer[0]['gltcurrency'])
