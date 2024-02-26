from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
import logging
import datetime

_logger = logging.getLogger(__name__)


class AssetLoanManagement(models.Model):
    _inherit = 'account.asset.asset'

    def _compute_loan_amount(self):
        if self.emi and self.loan_tenure and self.down_payment_amount:
            self.loan_amount = (self.emi * self.loan_tenure)

    # @api.multi
    @api.depends('fleet_vehicle_id')
    def _count_loan(self):
        for asset in self:
            res = self.env['account.move'].search_count([('fleet_vehicle_id', '=', asset.fleet_vehicle_id.id), ('loan_id', '=', asset.id)])
            asset.loan_count = res or 0

    is_fleet = fields.Boolean(string='Generate From Fleet?')
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle ID')
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal')
    asset_cost = fields.Float(string='Cost of the Asset')
    loan_tenure = fields.Integer(string='Loan Tenure(Months)')
    first_insatllement_date = fields.Datetime(string='First Installment Date')
    loan_liability_account_id = fields.Many2one('account.account', string='Loan Liability Account')
    bank_expenses_account_id = fields.Many2one('account.account', string='Bank Expenses Account')
    interest_percentage = fields.Float(string='Interest %')
    down_payment = fields.Float(string='Down Payment')
    emi = fields.Float(string='Monthly Installment')
    # loan_amount = fields.Float(compute='_compute_loan_amount', string="Total Loan Amount", readonly=True)
    loan_amount = fields.Float(string="Total Loan Amount")
    bank_charges = fields.Float(string='Bank Charges')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    vendor_ref = fields.Many2one('account.move', string='Vendor Bill Reference')
    vendor_date = fields.Date(string='Vendor Bill Date')

    debit_account_id = fields.Many2one('account.account', string='Debit Account')
    credit_account_id = fields.Many2one('account.account', string='Credit Account')

    loan_liability_account_id = fields.Many2one('account.account', string='Loan Liability Account')
    bank_expenses_account_id = fields.Many2one('account.account', string='Bank Expenses Account')

    purch_id = fields.Many2one('purchase.order')

    loan_count = fields.Integer(compute='_count_loan', string="Rents")

    # here we need to add the down payment
    @api.onchange('fleet_vehicle_id')
    def onchange_vehicle_id(self):
        if self.fleet_vehicle_id and not self.name:
            self.name = self.fleet_vehicle_id.name
            # down_payment_amount = self.fleet_vehicle_id.down_payment
            down_payment_amount = 100
            # asset_cost = self.fleet_vehicle_id.vehicle_cost_price
            asset_cost = 100
            self.down_payment_amount = down_payment_amount
            self.asset_cost = asset_cost
            self.value = asset_cost
            self.loan_amount = asset_cost - down_payment_amount

    @api.onchange('interest_percentage')
    def onchange_interest_percentage(self):
        if self.loan_amount and self.interest_percentage and self.loan_tenure:
            interest_percentage = self.interest_percentage / 100
            self.emi = (self.loan_amount + (
                    self.loan_amount * interest_percentage) * self.loan_tenure / 12) / self.loan_tenure
            # (P + (P* 0.05)*60/12)/60

    @api.onchange('loan_amount')
    def onchange_loan_amount(self):
        if self.loan_amount and self.interest_percentage and self.loan_tenure:
            interest_percentage = self.interest_percentage / 100
            self.emi = (self.loan_amount + (self.loan_amount * interest_percentage) * self.loan_tenure / 12) / self.loan_tenure

    @api.onchange('loan_tenure')
    def onchange_loan_tenure(self):
        if self.loan_tenure > 0:
            if self.loan_amount and self.interest_percentage:
                interest_percentage = self.interest_percentage / 100
                self.emi = (self.loan_amount + (self.loan_amount * interest_percentage) * self.loan_tenure / 12) / self.loan_tenure
        else:
            raise ValidationError('Please Give a Proper Value')

    @api.onchange('down_payment')
    def onchange_down_payment_amount(self):
        if self.down_payment and self.asset_cost:
                self.loan_amount = self.asset_cost - self.down_payment
        else:
            raise ValidationError('Please type Valid Values')

    @api.onchange('asset_cost')
    def onchange_asset_cost(self):
        if self.down_payment and self.asset_cost:
            self.loan_amount = self.asset_cost - self.down_payment

    # Open Loan Account entries
    # @api.multi
    def open_loan_entries(self):
        move_ids = []
        moves = account_move_obj.search_count(
            [('fleet_vehicle_id', '=', record.fleet_vehicle_id.id), ('loan_id', '=', record.id)])
        if moves:
            for move in moves:
                move_ids.append(move.id)
        return {
            'name': _('Journal Entries for Loans'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }

    # Generate Draft Journal entries for loan
    def generate_loan_accounting_entries(self):
        company_id = self.env.user.company_id
        msg1 = ("This is my debug message loan self.env.user.company_id.id! %s", company_id.id)
        _logger.error(msg1)

        transfer_account_id = company_id.transfer_account_id
        analytic_account_id = self.fleet_vehicle_id.analytic_account_id.id
        analytic_line_amount = (self.down_payment) * (-1)
        analytic_line_obj = self.env['account.analytic.line'].search(
            [('account_id', '=', analytic_account_id), ('name', '=', 'Vehicle Downpayment')])
        # if not analytic_line_obj:
        #     self.env['account.analytic.line'].create({'name':'Vehicle Downpayment', 'account_id':analytic_account_id, 'date':datetime.today(), 'amount':analytic_line_amount})

        msg1 = ("This is my debug message loan transfer_account_id! %s", transfer_account_id)
        _logger.error(msg1)
        # Journal entry for total loan amounts
        debit_vals_loan_amount = {
            'name': "Loan for " + self.name,
            # 'debit': abs((self.emi * self.loan_tenure) - self.loan_amount),
            'debit': abs(self.loan_amount),
            'credit': 0.0,
            'account_id': transfer_account_id.id, }
        # msg1 = ("This is my debug message loan debit_vals_bank_expenses! %s", debit_vals_bank_expenses)
        # _logger.error(msg1)

        # debit_vals_loan_amount = {
        #     'name': "Total Loan Payable for " + self.name,
        #     'debit': abs(self.loan_amount),
        #     'credit': 0.0,
        #     'account_id': transfer_account_id.id,}

        # msg1 = ("This is my debug message loan debit_vals_transfer_account_amount! %s", debit_vals_transfer_account_amount)
        # _logger.error(msg1)

        credit_vals_loan_amount = {
            'name': "Total Loan Payable for " + self.name,
            'debit': 0.0,
            'credit': abs(self.loan_amount),
            'account_id': self.loan_liability_account_id.id, }


        # msg1 = ("This is my debug message loan credit_vals! %s", credit_vals)
        # _logger.error(msg1)

        vals = {
            'journal_id': self.bank_journal_id.id,
            'fleet_vehicle_id': self.fleet_vehicle_id.id,
            'date': self.first_insatllement_date,
            'loan_id': self.id,
            'ref': "Loan for " + self.name,
            'state': 'draft',
            'line_ids': [(0, 0, debit_vals_loan_amount), (0, 0, credit_vals_loan_amount)]}



        msg1 = ("This is my debug message loan vals! %s", vals)
        _logger.error(msg1)

        move = self.env['account.move'].create(vals)

        # Journal entry for emi
        for x in range(self.loan_tenure):
            due_date = datetime.datetime.strptime(str(self.first_insatllement_date), DT) + relativedelta(
                months=int(x + 1))

            debit_vals_loan_liability = {
                'name': "Principal Against Loan for" + self.name,
                'debit': abs((self.loan_amount / self.loan_tenure)),
                'credit': 0.0,
                'account_id': self.loan_liability_account_id.id, }

            debit_vals_bank_expenses = {
                'name': "Interest Against Loan for " + self.name,
                'debit': abs(((self.emi * self.loan_tenure) - self.loan_amount) / self.loan_tenure),
                'credit': 0.0,
                'account_id': self.bank_expenses_account_id.id, }

            credit_vals = {
                'name': "EMI for " + self.name,
                'debit': 0.0,
                'credit': abs(self.emi),
                'account_id': self.bank_journal_id.payment_credit_account_id.id, }

            vals = {
                'journal_id': self.bank_journal_id.id,
                'fleet_vehicle_id': self.fleet_vehicle_id.id,
                'loan_id': self.id,
                'ref': "EMI for " + self.name,
                'date': due_date,
                'state': 'draft',
                'line_ids': [(0, 0, debit_vals_loan_liability), (0, 0, debit_vals_bank_expenses), (0, 0, credit_vals)]}
            # msg1 = ("This is my debug message loan vals! %s ",vals)
            # _logger.error(msg1)
            move = self.env['account.move'].create(vals)
            analytic_line_amount = (self.emi) * (-1)
            self.env['account.analytic.line'].create(
                {'name': 'Vehicle Loan EMI', 'account_id': analytic_account_id, 'date': due_date,
                 'amount': analytic_line_amount})






    # @api.multi
    def open_loan_entries(self):
        # move_ids = []
        # for asset in self:
        #     for depreciation_line in asset.depreciation_line_ids:
        #         if depreciation_line.move_id:
        #             move_ids.append(depreciation_line.move_id.id)
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('loan_id', '=', self.id)],
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle ID')
    loan_id = fields.Many2one('account.asset.asset', string='Loan ID')
