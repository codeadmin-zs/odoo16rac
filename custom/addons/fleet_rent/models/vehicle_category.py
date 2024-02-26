from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning
import logging
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


_logger = logging.getLogger(__name__)


class VehicleProductCategoryType(models.Model):
    _name = 'fleet.category.vehicle.type'

    name = fields.Char(string='Vehicle Type')


# class VehicleProductCategoryClass(models.Model):
#     _name = 'fleet.category.vehicle.class'
#
#     name = fields.Char(string='Vehicle Class')


class VehicleProductCategoryTransmission(models.Model):
    _name = 'fleet.category.vehicle.transmission'

    name = fields.Char(string='Transmission Drive')


class VehicleProductCategoryFuel(models.Model):
    _name = 'fleet.category.vehicle.fuel'

    name = fields.Char(string='Fuel')


class InsuranceType(models.Model):
    _name = 'insurance.type'

    name = fields.Char(string='Name')


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    attachment_id = fields.Many2one('fleet.vehicle')
    attachment_id_2 = fields.Many2one('fleet.vehicle')

    # @api.multi
    def copy(self, default=None):
        raise Warning(_("You can\'t duplicate record !!"))


class EngineHistory(models.Model):
    _name = 'engine.history'

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    previous_engine_no = fields.Char(string='Previous Engine No')
    new_engine_no = fields.Char(string='New Engine No')
    changed_date = fields.Date(string='Change Date')
    note = fields.Text('Notes', translate=True)
    workorder_id = fields.Many2one('fleet.vehicle.log.services',
                                   string='Work Order')

    # @api.multi
    def copy(self, default=None):
        raise Warning(_("You can\'t duplicate record !!"))

    # @api.multi
    def unlink(self):
        raise Warning(_("You can\'t delete record !!"))


class VinHistory(models.Model):
    _name = 'vin.history'

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    previous_vin_no = fields.Char(string='Previous Vin No', translate=True)
    new_vin_no = fields.Char(string='New Vin No', translate=True)
    changed_date = fields.Date(string='Change Date')
    note = fields.Text(string='Notes', translate=True)
    workorder_id = fields.Many2one('fleet.vehicle.log.services',
                                   string='Work Order')

    # @api.multi
    def copy(self, default=None):
        raise Warning(_("You can\'t duplicate record!"))

    # @api.multi
    def unlink(self):
        raise Warning(_("You can\'t delete record !!"))


class ColorHistory(models.Model):
    _name = 'color.history'

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    previous_color_id = fields.Many2one('color.color', string="Previous Color")
    current_color_id = fields.Many2one('color.color', string="New Color")
    changed_date = fields.Date(string='Change Date')
    note = fields.Text(string='Notes', translate=True)
    workorder_id = fields.Many2one('fleet.vehicle.log.services',
                                   string='Work Order')

    # @api.multi
    def copy(self, default=None):
        raise Warning(_("You can\'t duplicate record !!"))

    # @api.multi
    def unlink(self):
        raise Warning(_("You can\'t delete record !!"))


class TireHistory(models.Model):
    _name = 'tire.history'

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    previous_tire_size = fields.Char(string='Previous Tire Size',
                                     size=124, translate=True)
    new_tire_size = fields.Char(string="New Tire Size", size=124,
                                translate=True)
    previous_tire_sn = fields.Char(string='Previous Tire Serial', size=124,
                                   translate=True)
    new_tire_sn = fields.Char(string="New Tire Serial", size=124)
    previous_tire_issue_date = fields.Date(
        string='Previous Tire Issuance Date')
    new_tire_issue_date = fields.Date(string='New Tire Issuance Date')
    changed_date = fields.Date(string='Change Date')
    note = fields.Text(string='Notes', translate=True)
    workorder_id = fields.Many2one('fleet.vehicle.log.services',
                                   string='Work Order')

    # @api.multi
    def copy(self, default=None):
        raise Warning(_("You can\'t duplicate record !!"))

    # @api.multi
    def unlink(self):
        raise Warning(_("You can\'t delete record !!"))


class BatteryHistory(models.Model):
    _name = 'battery.history'

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    previous_battery_size = fields.Char(string='Previous Battery Size',
                                        size=124)
    new_battery_size = fields.Char(string="New Battery Size", size=124)
    previous_battery_sn = fields.Char(string='Previous Battery Serial',
                                      size=124)
    new_battery_sn = fields.Char(string="New Battery Serial", size=124)
    previous_battery_issue_date = fields.Date(
        string='Previous Battery Issuance Date')
    new_battery_issue_date = fields.Date(string='New Battery Issuance Date')
    changed_date = fields.Date(string='Change Date')
    note = fields.Text(string='Notes', translate=True)
    workorder_id = fields.Many2one('fleet.vehicle.log.services',
                                   string='Work Order')

    # @api.multi
    def copy(self, default=None):
        raise Warning(_("You can\'t duplicate record !!"))

    # @api.multi
    def unlink(self):
        raise Warning(_("You can\'t delete record !!"))


class NextIncrementNumber(models.Model):
    _name = 'next.increment.number'

    def _default_vehicle_id_for_increment(self):
        if self.env.context.get('default_vehicle_id', False):
            return self.env['fleet.vehicle'].browse(self.env.context.get('default_vehicle_id'))

    name = fields.Char(string='Name', size=64, translate=True)
    # vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Id')
    number = fields.Float(string='Odometer Increment')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Id', default=_default_vehicle_id_for_increment)

    # @api.multi
    def copy(self, default=None):
        raise Warning(_("You can\'t duplicate record !"))
#

class MaintenanceType(models.Model):
    _name = 'maintenance.type'

    name = fields.Char(
        string='Maintenance Type',
        size=50,
        required=True)
    main_cost = fields.Boolean(
        string='Recurring cost',
        help='Check if the recuring cost involve')
    cost = fields.Float(
        string='Maintenance Cost',
        help='insert the cost')


class MaintenanaceCost(models.Model):
    _name = 'maintenance.cost'

    maint_type = fields.Many2one(
        comodel_name='maintenance.type',
        string='Maintenance Type')
    cost = fields.Float(
        string='Maintenance Cost',
        help='insert the cost')
    tenancy = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Rental Vehicle')

    @api.onchange('maint_type')
    def onchange_property_id(self):
        """
        This Method is used to set maintenance type related fields value,
        on change of property.
        @param self: The object pointer
        """
        if self.maint_type:
            self.cost = self.maint_type.cost or 0.00


class TenancyRentSchedule(models.Model):
    _name = "tenancy.rent.schedule"
    _rec_name = "tenancy_id"
    _order = 'start_date'

    # @api.one
    @api.depends('move_id')
    def _get_move_check(self):
        self.move_check = bool(self.move_id)

    def _default_tenancy_state(self):
        if self.env.context.get('active_id', False):
            tenancy_id = self.env['account.analytic.account'].browse(self.env.context.get('active_id'))
            if self.tenancy_id:
                return tenancy_id.state

    @api.model
    def create(self, vals):
        """
        This Method is used to overrides orm create method,
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        res = super(TenancyRentSchedule, self).create(vals)
        res.create_invoice()
        return res

    def _get_default_pen_amount(self):
        if self.amount:
            self.pen_amt = self.amount

    # @api.multi
    def print_invoice(self):
        if self.invc_id:
            self.invc_id.invoice_print()

    state = fields.Char(string='Status', default=_default_tenancy_state)
    note = fields.Text(string='Notes', help='Additional Notes.')
    currency_id = fields.Many2one(comodel_name='res.currency',
                                  string='Currency')
    amount = fields.Float(string='Amount', default=0.0, compute="_compute_total_invoice_line_amount",
                          currency_field='currency_id', help="Rent Amount.")
    start_date = fields.Datetime(string='Date', help='Start Date.', default=lambda s: datetime.now())
    end_date = fields.Date(string='End Date', help='End Date.')
    cheque_detail = fields.Char(string='Cheque Detail', size=30)
    move_check = fields.Boolean(compute='_get_move_check', method=True,
                                string='Posted', store=True, default=False)
    rel_tenant_id = fields.Many2one(comodel_name='res.partner',
                                    string="Tenant")
    move_id = fields.Many2one(comodel_name='account.move',
                              string='Depreciation Entry')
    vehicle_id = fields.Many2one(comodel_name='fleet.vehicle',
                                 string='Vehicle',
                                 help='Vehicle Name.')
    tenancy_id = fields.Many2one(comodel_name='account.analytic.account',
                                 string='Rental Vehicle',
                                 help='Rental Vehicle Name.')
    paid = fields.Boolean(string='Paid',
                          help="True if this rent is paid by tenant", default=False)
    invc_id = fields.Many2one('account.move', string='Invoice')
    inv = fields.Boolean(string='Invoice', default=False)
    single_inv = fields.Boolean(string='Invoice', default=False)
    pen_amt = fields.Float(string='Pending Amount', help='Pending Amount.',
                           store=True)
    duration = fields.Float(string='Duration', default=0.0)

    @api.depends('invc_id.invoice_line_ids', 'invc_id.invoice_line_ids.price_subtotal')
    def _compute_total_invoice_line_amount(self):
        """
        This method is used to calculate Total Rent of current Tenancy.
        @param self: The object pointer
        @return: Calculated Total Rent.
        """
        for each in self:
            each.amount = each.invc_id.amount_total
            each.pen_amt = each.invc_id.amount_residual
            # if each.state == 'draft':
            #     self.pen_amt = self.amount

    # @api.multi
    def create_invoice(self):
        """
        Create invoice for Rent Schedule.
        """
        journal_ids = self.env['account.journal'].search([('type', '=', 'sale')])
        if not self.tenancy_id.vehicle_id.income_acc_id.id:
            raise Warning(_('Please Configure Income Account from Vehicle.'))
        inv_add_prod = []
        if self.tenancy_id.extra_charges_ids:
            for each in self.tenancy_id.extra_charges_ids:
                if self.tenancy_id.invoice_policies == 'periodic' and self.tenancy_id.extra_charges_ids.unit_measure.name == 'Months':
                    start_date = self.tenancy_id.date_start
                    inv_date = self.start_date-timedelta(days=1)
                    diff_date = inv_date-start_date
                    closing_date = self.tenancy_id.date
                    first_day_of_next_month = date(closing_date.year, closing_date.month, 1)
                    diff_closing_date = self.tenancy_id.date.date() - first_day_of_next_month
                    if 0 < diff_date.days < 30:
                        unit_price = each.unit_price/30 * diff_date.days
                    elif closing_date == inv_date+timedelta(days=1):
                        unit_price = each.unit_price/30 * (diff_closing_date.days + 1) \
                            if diff_closing_date.days > 0 else each.unit_price
                    else:
                        unit_price = each.unit_price
                else:
                    unit_price = each.unit_price
                if not each.line_added_status:
                    self.vehicle_id.license_plate if self.state == 'replacement' else ' '
                    inv_line_main = {
                        # 'origin': 'tenancy.rent.schedule',
                        'name': each.additional_charge_product_id.name,
                        'price_unit': unit_price or 0.00,
                        # 'price_unit': self.tenancy_id.rent or 0.00,
                        'price_subtotal': each.cost/self.tenancy_id.duration or 0.00 if self.tenancy_id.invoice_policies == 'periodic' else each.cost or 0.00,
                        'product_uom_id': each.unit_measure.id,
                        'quantity': each.product_uom_qty/self.tenancy_id.duration if self.tenancy_id.invoice_policies == 'periodic' else each.product_uom_qty,
                        'account_id': self.tenancy_id.vehicle_id.income_acc_id.id or False,
                        'analytic_account_id': self.vehicle_id.analytic_account_id.id or False,
                        'tax_ids': each.additional_charge_product_id.taxes_id,
                        'description': each.description,
                    }
                    if self.tenancy_id.multi_prop:
                        for data in self.tenancy_id.prop_id:
                            for account in data.property_ids.income_acc_id:
                                inv_line_main.update({'account_id': account.id})
                    inv_add_prod.append((0, 0, inv_line_main))
        if self.tenancy_id.additional_charges > 0:
            for each in self.tenancy_id.additional_rental_charges_ids:
                if not each.line_added_status:
                    inv_line_main = {
                        'name': each.additional_charge_product_id.name,
                        # 'price_unit': each.unit_price or 0.00, changed price of invoice
                        'price_unit': self.tenancy_id.rent or 0.00,
                        'product_uom_id': each.unit_measure.id,
                        'price_subtotal': each.cost/self.tenancy_id.duration or 0.00 if self.tenancy_id.invoice_policies == 'periodic' else each.cost or 0.00,
                        'quantity': each.product_uom_qty/self.tenancy_id.duration if self.tenancy_id.invoice_policies == 'periodic' else each.product_uom_qty,
                        'account_id': self.tenancy_id.vehicle_id.income_acc_id.id or False,
                        'analytic_account_id': self.vehicle_id.analytic_account_id.id or False,
                        'tax_ids': each.additional_charge_product_id.taxes_id,
                        'description': each.description,
                    }
                    if self.tenancy_id.multi_prop:
                        for data in self.tenancy_id.prop_id:
                            for account in data.property_ids.income_acc_id:
                                inv_line_main.update({'account_id': account.id})
                    inv_add_prod.append((0, 0, inv_line_main))

        inv_line_values = {
            'name': 'Vehicle Rental Charge',
            'price_unit': self.tenancy_id.rent or 0.00,
            'quantity': 1,
            'account_id': self.tenancy_id.vehicle_id.income_acc_id.id or False,
            'analytic_account_id': self.tenancy_id.vehicle_id.analytic_account_id.id or False,
            'tenancy_id': self.tenancy_id.id or False
        }
        if self.tenancy_id.multi_prop:
            for data in self.tenancy_id.prop_id:
                for account in data.property_ids.income_acc_id:
                    inv_line_values.update({'account_id': account.id})
        inv_values = {
            'partner_id': self.tenancy_id and self.tenancy_id.tenant_id and self.tenancy_id.tenant_id.id or False,
            'move_type': 'out_invoice',
            'fleet_vehicle_id': self.tenancy_id.vehicle_id.id or False,
            'date_invoice': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) or False,
            'invoice_date': self.start_date or False,
            'journal_id': journal_ids and journal_ids[0].id or False,
            'state': 'draft',
            'invoice_line_ids': inv_add_prod
        }
        acc_id = self.env['account.move'].create(inv_values)
        self.write({'invc_id': acc_id.id, 'inv': True, 'amount': acc_id.amount_total, 'pen_amt': acc_id.amount_total})
        if self.tenancy_id.rental_terms == 'spot':
            self.tenancy_id.account_move_line_ids = acc_id.line_ids
        context = dict(self._context or {})
        wiz_form_id = self.env.ref('account.view_move_form').id

        return {
            'view_type': 'form',
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invc_id.id,
            'type': 'ir.actions.act_window',
            'target':  'current',
            'context': context,
        }

    # @api.multi
    def open_invoice(self):
        context = dict(self._context or {})
        # wiz_form_id = self.env['ir.model.data'].get_object_reference(
        #     'account', 'invoice_form')[1]
        wiz_form_id = self.env.ref('account.view_move_form').id

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
    def create_move(self):
        """
        This button Method is used to create account move.
        @param self: The object pointer
        """
        move_line_obj = self.env['account.move.line']
        created_move_ids = []
        journal_ids = self.env['account.journal'].search(
            [('type', '=', 'sale')])
        for line in self:
            depreciation_date = datetime.now()
            company_currency = line.tenancy_id.company_id.currency_id.id
            current_currency = line.tenancy_id.currency_id.id
            sign = -1
            move_vals = {
                'name': line.tenancy_id.ref or False,
                'date': depreciation_date,
                'schedule_date': line.start_date,
                'journal_id': journal_ids and journal_ids.ids[0],
                'asset_id': line.tenancy_id.property_id.id or False,
                'source': line.tenancy_id.name or False,
            }
            move_id = self.env['account.move'].create(move_vals)
            if not line.tenancy_id.property_id.income_acc_id.id:
                raise Warning(
                    _('Please Configure Income Account from Property.'))
            cond1 = company_currency is not current_currency
            cond2 = -sign * line.tenancy_id.rent
            move_line_obj.create({
                'name': line.tenancy_id.name,
                'ref': line.tenancy_id.ref,
                'move_id': move_id.id,
                'account_id':
                line.tenancy_id.property_id.income_acc_id.id or False,
                'debit': 0.0,
                'credit': line.tenancy_id.rent,
                'journal_id': journal_ids and journal_ids.ids[0],
                'partner_id': line.tenancy_id.tenant_id.id or False,
                'currency_id': company_currency != current_currency and
                current_currency or False,
                'amount_currency': cond1 and cond2 or 0.0,
                'date': depreciation_date,
            })
            move_line_obj.create({
                'name': line.tenancy_id.name,
                'ref': 'Tenancy Rent',
                'move_id': move_id.id,
                'account_id':
                line.tenancy_id.tenant_id.property_account_receivable_id.id,
                'credit': 0.0,
                'debit': line.tenancy_id.rent,
                'journal_id': journal_ids and journal_ids.ids[0],
                'partner_id': line.tenancy_id.tenant_id.id or False,
                'currency_id': company_currency != current_currency and
                current_currency,
                'amount_currency': company_currency != current_currency and
                sign * line.tenancy_id.rent or 0.0,
                'analytic_account_id': line.tenancy_id.id,
                'date': depreciation_date,
                'asset_id': line.tenancy_id.property_id.id or False,
            })
            line.write({'move_id': move_id.id})
            created_move_ids.append(move_id.id)
            move_id.write({'ref': 'Tenancy Rent', 'state': 'posted'})
        return created_move_ids


class RentalWizardFleetAdditionalCharges(models.Model):
    _name = 'rental.wizard.fleet.additional.charges'

    additional_charge_product_id = fields.Many2one('product.product', string='Product',
                                                   required=True,
                                                   domain=[('product_tmpl_id.accessories_ok', '=', True)])
    agreement_id = fields.Many2one('account.analytic.account', string='Partner')
    cost = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        default=lambda self: self.env.user.company_id.currency_id.id,
        required=True)
    lot_id = fields.Many2one(
        'stock.lot',
        string="Serial Numbers", help="Only available serial numbers are suggested",
        domain="[('product_id', '=', additional_charge_product_id)]")
    product_uom_qty = fields.Float('Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    unit_measure = fields.Many2one(string='Unit Of Measure',
                                   related='additional_charge_product_id.product_tmpl_id.uom_id')
    taxes_id = fields.Many2one('account.tax', string='Taxes')
    unit_price = fields.Float('Unit Price')
    description = fields.Text(string='Description')
    line_added_status = fields.Boolean(default=False)

    @api.onchange('additional_charge_product_id')
    def accessories_product_cost(self):
        if self.additional_charge_product_id:
            duration_unit = self.agreement_id.duration_unit.capitalize() + 's'
            unit_obj = self.env['uom.uom'].search([('name', '=', duration_unit)])
            available_pricing = self.env['rental.pricing'].search(
                [('parent_product_template_id', '=', self.additional_charge_product_id.product_tmpl_id.id),
                 ('unit', '=', unit_obj.id)])[0]
            self.product_uom_qty = self.agreement_id.duration
            self.unit_price = available_pricing.price
            self.unit_measure = unit_obj
            self.taxes_id = available_pricing.tax_ids.id

    @api.depends('product_uom_qty', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.cost = line.product_uom_qty * line.unit_price
            taxes = line.taxes_id.compute_all(line.unit_price, line.currency_id, line.product_uom_qty,
                                              product=line.additional_charge_product_id)
            line.update({
                'cost': taxes['total_included'],
            })


class RentalWizardFleetExtraCharges(models.Model):
    _name = 'rental.wizard.extra.charges'

    additional_charge_product_id = fields.Many2one('product.product', string='Product',
                                                   required=True,
                                                   domain=[('product_tmpl_id.charges_ok', '=', True)])

    agreement_id = fields.Many2one('account.analytic.account', string='Partner')
    cost = fields.Float(string='Cost', digits=dp.get_precision('Product Price'))
    product_uom_qty = fields.Float('Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    unit_measure = fields.Many2one(string='Unit Of Measure',
                                   related='additional_charge_product_id.product_tmpl_id.uom_id')
    unit_price = fields.Float('Unit Price')
    description = fields.Text(string='Description')
    line_added_status = fields.Boolean(default=False)


class RentalWizardFleetAdditionalDrivers(models.Model):
    _name = 'fleet.additional.drivers'

    rental_id = fields.Many2one('account.analytic.account', string='Contract')
    additional_driver = fields.Many2one('res.partner', string='Driver', required=True)
    driving_license_number = fields.Char(string='Driving License Number',
                                         related='additional_driver.dl_number')
    description = fields.Text(string='Description')

class ReplaceVehicleLog(models.Model):
    _name = 'replace.vehicle.log'

    replace_id = fields.Many2one('account.analytic.account')
    re_vehicle = fields.Many2one('fleet.vehicle', string='Vehicle')
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    current_odometer = fields.Float(string='Starting Odometer')
    closing_odometer = fields.Float(string='Closing Odometer')

