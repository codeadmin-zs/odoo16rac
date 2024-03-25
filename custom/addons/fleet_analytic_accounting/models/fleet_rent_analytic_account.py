from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta
from datetime import date
from dateutil import tz
import time
import logging
import odoo.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.onchange('tenant_id')
    def _change_tenant(self):
        ten_id = self.env['sale.order'].search([('id', '=', self.sale_order_id.id)])
        ten_id.partner_id = self.tenant_id

    def _get_odometer(self):
        fleet_odometer_obj = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = fleet_odometer_obj.search([
                ('vehicle_id', '=', record.vehicle_id.id)], limit=1,
                order='value desc')
            if vehicle_odometer:
                record.odometer = vehicle_odometer.value
            else:
                record.odometer = 0

    def _set_odometer(self):
        fleet_odometer_obj = self.env['fleet.vehicle.odometer']
        for record in self:
            vehicle_odometer = fleet_odometer_obj.search(
                [('vehicle_id', '=', record.vehicle_id.id)],
                limit=1, order='value desc')
            if record.odometer < vehicle_odometer.value:
                raise Warning(('User Error!\nYou can\'t enter odometer less \
                than previous odometer %s !') % (vehicle_odometer.value))
            if record.odometer:
                date = fields.Date.context_today(record)
                data = {'value': record.odometer, 'date': date,
                        'vehicle_id': record.vehicle_id.id}
                fleet_odometer_obj.create(data)

    @api.onchange('')
    def onchange_vehicle_id(self):
        for rec in self:
            fleet_odometer_obj = self.env['fleet.vehicle.odometer']
            vehicle_odometer = fleet_odometer_obj.search([
                ('vehicle_id', '=', rec.vehicle_id.id)], limit=1,
                order='value desc')
            if rec.vehicle_id:
                rec.current_odometer = vehicle_odometer.value
                duration_unit = rec.duration_unit.capitalize() + 's'
                unit_obj = self.env['uom.uom'].search([('name', '=', duration_unit)])
                product_name = self.vehicle_id.vehicle_prodcut_template_id.name + ': ' + (
                    'Daily' if duration_unit == 'Days' else self.duration_unit.capitalize()) + ' Rate'
                product_tmpl = self.env['product.template'].search([('name', '=', product_name)])
                rental_pricing = self.env['rental.pricing'].search([
                    ('parent_product_template_id', '=', rec.vehicle_id.vehicle_prodcut_template_id.id),
                    ('product_template_id', '=', product_tmpl.id),
                    ('unit', '=', unit_obj.id)])
                rec.rent = rental_pricing.price

    @api.onchange('tenant_id')
    def check_drivers(self):
        if self.tenant_id.tenant and self.tenant_id.is_driver:
            drivers_obj = self.env['fleet.additional.drivers']
            new_drivers = drivers_obj.create({'additional_driver': self.tenant_id.id,
                                              'driving_license_number': self.tenant_id.dl_number,
                                              'rental_id': self.id})
            self.additional_drivers_ids = new_drivers

    @api.depends('rent_schedule_ids.invc_id')
    def _compute_scheduled_invoices_status(self):
        for rec in self:
            inv_status = False
            if not self.rent_schedule_ids:
                rec.update({'scheduled_invoices_status': False})
            for line in rec.rent_schedule_ids:
                if line.invc_id and line.invc_id.state in ['posted']:
                    rec.update({'scheduled_invoices_status': True})
                else:
                    rec.update({'scheduled_invoices_status': False})

    @api.depends('additional_rental_charges_ids.cost', 'extra_charges_ids.cost')
    def _compute_additional_charges(self):
        for rec in self:
            charge_total = 0.0
            if rec.additional_rental_charges_ids:
                for line in rec.additional_rental_charges_ids:
                    charge_total += line.cost
            if rec.extra_charges_ids:
                for line in rec.extra_charges_ids:
                    charge_total += line.cost
            rec.update({'additional_charges': charge_total})

    @api.depends('duration_unit', 'duration')
    def _compute_pricing(self):

        self.pricing_id = False
        if self.duration_unit:
            unit = self.duration_unit.capitalize() + 's'
        unit_obj = self.env['uom.uom'].search([('name', '=', unit)])
        for wizard in self:
            if wizard.vehicle_id.vehicle_prodcut_id:
                product_name = self.vehicle_id.vehicle_prodcut_template_id.name + ': ' + (
                    'Daily' if unit == 'Days' else self.duration_unit.capitalize()) + ' Rate'
                product_tmpl = self.env['product.template'].search([('name', '=', product_name)])
                available_pricing = self.env['rental.pricing'].search(
                    [('parent_product_template_id', '=', self.vehicle_id.vehicle_prodcut_template_id.id),
                     ('unit', '=', unit_obj.id), ('product_template_id', '=', product_tmpl.id)])
                wizard.pricing_id = available_pricing
                msg1 = ("This is my debug message wizard.pricing_id')! %s", wizard.pricing_id)
                _logger.error(msg1)

    # @api.multi
    @api.depends('deposit')
    def _get_deposit(self):
        """
        This method is used to set deposit return and deposit received
        boolean field accordingly to current Tenancy.
        @param self: The object pointer
        """
        for tennancy in self:
            payment_ids = self.env['account.payment'].search([('tenancy_id', '=', tennancy.id), ('state', '=', 'posted')])
            if payment_ids and payment_ids.ids:
                for payment in payment_ids:
                    tennancy.deposit_received = True
                    tennancy.deposit_receipt = payment
                    tennancy.deposit = payment.amount
            else:
                tennancy.deposit_received = False

    @api.onchange('pricing_id', 'currency_id', 'duration', 'duration_unit', 'additional_charges', 'vehicle_id')
    def _compute_unit_price(self):
        for wizard in self:
            if wizard.pricing_id and wizard.duration > 0:
                rent = wizard.pricing_id._compute_price(wizard.duration, wizard.duration_unit)
                if wizard.currency_id != wizard.pricing_id.currency_id:
                    wizard.rent = wizard.pricing_id.currency_id._convert(
                        from_amount=rent,
                        to_currency=wizard.currency_id,
                        company=wizard.company_id,
                        date=date.today())
                else:
                    wizard.rent = rent
            elif wizard.duration > 0:
                if self.duration_unit and wizard.vehicle_id:
                    duration_unit = self.duration_unit.capitalize() + 's'
                    unit_obj = self.env['uom.uom'].search([('name', '=', duration_unit)])
                    product_name = self.vehicle_id.vehicle_prodcut_template_id.name + ': ' + (
                        'Daily' if duration_unit == 'Days' else self.duration_unit.capitalize()) + ' Rate'
                    product_tmpl = self.env['product.template'].search([('name', '=', product_name)])
                    available_pricing = self.env['rental.pricing'].search(
                        [('parent_product_template_id', '=', self.vehicle_id.vehicle_prodcut_template_id.id),
                         ('unit', '=', unit_obj.id), ('product_template_id', '=', product_tmpl.id)])
                    wizard.rent = available_pricing.price
            msg1 = ("This is my debug message wizard.rent')! %s", wizard.rent)
            _logger.error(msg1)

    @api.depends('amount_return')
    def amount_return_compute(self):
        """
        When you change Deposit field value, this method will change
        amount_fee_paid field value accordingly.
        @param self: The object pointer
        """
        for rec in self:
            if rec.amount_return > 0.00:
                rec.deposit_return = True
            else:
                rec.deposit_return = False

    # @api.multi
    def change_color(self):
        for color in self:
            if color.state == 'new':
                color.color = 0
            elif color.state == 'open':
                color.color = 2
            elif color.state == 'pending':
                color.color = 1
            elif color.state == 'close':
                color.color = 5
            elif color.state == 'cancelled':
                color.color = 4

    # @api.multi
    @api.depends('date_start', 'duration', 'duration_unit')
    def _create_date(self):
        for rec in self:
            # msg1 = ("This is my debug message wizard pickup_date! %s"),rec.pickup_date
            # _logger.error(msg1)
            if rec.date_start:
                if rec.duration_unit == 'hour':
                    to_date = \
                        datetime.strptime(str(rec.date_start), DT) + \
                        relativedelta(hours=int(rec.duration))
                    # msg1 = ("This is my debug message wizard pickup_date! %s"),to_date
                    # _logger.error(msg1)
                    rec.date = to_date
                if rec.duration_unit == 'day':
                    to_date = \
                        datetime.strptime(str(rec.date_start), DT) + \
                        relativedelta(days=int(rec.duration))
                    # msg1 = ("This is my debug message wizard pickup_date! %s"),to_date
                    # _logger.error(msg1)
                    rec.date = to_date
                if rec.duration_unit == 'week':
                    to_date = \
                        datetime.strptime(str(rec.date_start), DT) + \
                        relativedelta(weeks=int(rec.duration))
                    # msg1 = ("This is my debug message wizard pickup_date! %s"),to_date
                    # _logger.error(msg1)
                    rec.date = to_date
                if rec.duration_unit == 'month':
                    to_date = \
                        datetime.strptime(str(rec.date_start), DT) + \
                        relativedelta(months=int(rec.duration))
                    # msg1 = ("This is my debug message wizard pickup_date! %s"),to_date
                    # _logger.error(msg1)
                    rec.date = to_date
        return True

    # @api.one
    @api.depends('rent_schedule_ids')
    def _total_amount_rent(self):
        """
        This method is used to calculate Total Rent of current Tenancy.
        @param self: The object pointer
        @return: Calculated Total Rent.
        """
        tot = 0.00
        if self.rent_schedule_ids and self.rent_schedule_ids.ids:
            for propety_brw in self.rent_schedule_ids:
                tot += propety_brw.amount
        self.total_rent = tot

    # @api.multi
    @api.depends('cost_id')
    def _total_cost_maint(self):
        """
        This method is used to calculate total maintenance
        boolean field accordingly to current Tenancy.
        @param self: The object pointer
        """
        total = 0
        for data in self:
            for data_1 in data.cost_id:
                total += data_1.cost
            data.main_cost = 0.0

    @api.model
    def rent_send_mail(self):
        model_obj = self.env['ir.model.data']
        send_obj = self.env['mail.template']
        rent_obj = self.env['account.analytic.account']
        res = model_obj.get_object_reference('fleet_rent',
                                             'email_template_edi_rent')
        server_obj = self.env['ir.mail_server']
        record_obj = model_obj.get_object_reference('fleet_rent',
                                                    'ir_mail_server_service')
        rec_date = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
        vehicle_ids = rent_obj.search([('date', '=', rec_date)])
        temp_rec = False
        email_from_brw = ''
        if record_obj:
            email_from_brw = server_obj.browse(record_obj[1])
        if res:
            temp_rec = send_obj.browse(res[1])
        for rec in vehicle_ids:
            email_from = email_from_brw.smtp_user
            if not email_from:
                raise Warning(_("Warning"), _("May be Out Going Mail server is not configured."))
            if vehicle_ids and temp_rec:
                temp_rec.send_mail(rec.id, force_send=True)
        return True

    # @api.one
    @api.depends('prop_id', 'multi_prop')
    def _total_prop_rent(self):
        tot = 0.00
        if self._context.get('is_tenancy_rent'):
            prop_val = self.prop_ids.ground_rent or 0.0
        else:
            prop_val = self.property_id.ground_rent or 0.0
        for pro_record in self:
            if self.multi_prop:
                for prope_ids in pro_record.prop_id:
                    tot += prope_ids.ground
                pro_record.rent = tot + prop_val
            else:
                pro_record.rent = prop_val

    # @api.multi
    @api.depends('account_move_line_ids')
    def _total_credit_amt_calc(self):
        """
        This method is used to calculate Total credit amount.
        @param self: The object pointer
        """
        total = 0.0
        for tenancy_brw in self:
            if tenancy_brw.account_move_line_ids and \
                    tenancy_brw.account_move_line_ids.ids:
                for debit_amt in tenancy_brw.account_move_line_ids:
                    total += debit_amt.credit
            tenancy_brw.total_credit_amt = total

    # @api.multi
    @api.depends('account_move_line_ids')
    def _total_deb_cre_amt_calc(self):
        """
        This method is used to calculate Total income amount.
        @param self: The object pointer
        """
        total = 0.0
        for tenancy_brw in self:
            total = tenancy_brw.total_debit_amt - tenancy_brw.total_credit_amt
            tenancy_brw.total_deb_cre_amt = total

    # @api.multi
    def _compute_outsatanding_days(self):
        for rec in self:
            if rec.date:
                curr_date = datetime.now()
            if rec.date:
                if datetime.strptime(str(rec.date), DT) < curr_date and rec.state == 'open':
                    self.has_outstanding_days = True
                else:
                    self.has_outstanding_days = False

    # @api.multi
    @api.depends('account_move_line_ids')
    def _total_debit_amt_calc(self):
        """
        This method is used to calculate Total debit amount.
        @param self: The object pointer
        """
        total = 0.0
        for tenancy_brw in self:
            if tenancy_brw.account_move_line_ids and \
                    tenancy_brw.account_move_line_ids.ids:
                for debit_amt in tenancy_brw.account_move_line_ids:
                    total += debit_amt.debit
            tenancy_brw.total_debit_amt = total

    # def _get_vehicles(self):
    #     all_vehicles = self.env['fleet.vehicle'].search([('state_id', '=', 6)])
    #     return {'domain': {'vehicle_id': [('id', 'in', all_vehicles.ids)]}}

    # @api.onchange('rental_terms')
    # def onchange_rental_terms(self):
    #     if self.rental_terms == 'long_term':
    #         self.vehicle_id = False
    #         all_vehicles = self.env['fleet.vehicle'].search([('state_id', '!=', 8)])
    #         return {'domain': {'vehicle_id': [('id', 'in', all_vehicles.ids)]}}

    @api.depends('tenant_id')
    def _compute_vehicle_name(self):
        for record in self:
            if not record.name:
                if record.tenant_id and record.ten_date:
                    record.name = record.tenant_id.name + '-' + record.ten_date.strftime(DT)

    @api.depends('tenant_id')
    def _set_vehicle_name(self):
        for record in self:
            if record.tenant_id:
                record.name = record.tenant_id.name + '-' + record.vehicle_id.name

    plan_id = fields.Many2one('account.analytic.plan',string='Plan',check_company=True,required=True,default=1)
    name = fields.Char(string='Analytic Account', compute='_set_vehicle_name',
                       index=True, required=True, tracking=True, store=True)
    vehicle_brand = fields.Many2one('fleet.vehicle.model.brand', string="Fleet Brand", size=50,
                                    related='vehicle_id.model_id.brand_id', store=True, readonly=True)
    color = fields.Integer(string='Color', compute='change_color')
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Last Odometer',
                            help='Odometer measure of the vehicle at the moment of this log')
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehicle', domain=[('state_id.name', '=', 'Available')],
        help="Name of Vehicle.")
    new_vehicle_id = fields.Many2one(comodel_name='fleet.vehicle',
                                     string='Vehicle', domain=[('state_id.name', '=', 'Available')],
                                     help="Name of Vehicle.")
    state = fields.Selection(
        [('draft', 'Booked'), ('hand_over', 'Hand Over'),
         ('open', 'In Progress'), ('return', 'Return'), ('pending', 'To Renew'),
         ('close', 'Closed'), ('cancelled', 'Cancelled')],
        string='Status',
        required=True,
        copy=False,
        default='draft', track_visibility='onchange')
    from_sale_order = fields.Boolean(default=False)
    rental_terms = fields.Selection(
        [('short_term', 'Short Term'),
         ('long_term', 'Long Term'), ('spot', 'Spot Rental'),
         ('online', 'Online Booking')],
        string='Rental Type',
        required=True,
        default='spot', track_visibility='onchange')

    rent_entry_chck = fields.Boolean(
        string='Rent Entries Check',
        default=False)
    cr_rent_btn = fields.Boolean('Hide Rent Button')
    multi_prop = fields.Boolean(
        string='Multiple Property',
        help="Check this box Multiple property.")
    is_property = fields.Boolean(
        string='Is Property?')
    invc_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice')
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id', store=True)
    # vehicle_image = fields.Binary(related="vehicle_id.image",
    #                               string="Vehicle Image")
    # odometer_unit = fields.Selection(
    #     related='vehicle_id.odometer_unit',
    #     help='Unit of the odometer ', store=True)
    deposit = fields.Float(
        string='Deposit',
        default=0.0,
        copy=False,
        readonly=True,
        currency_field='currency_id',
        help="Deposit amount for Rental Vehicle.")
    amount_return = fields.Float(
        string='Deposit Returned',
        copy=False,
        currency_field='currency_id',
        help="Deposit Returned amount for Rental Vehicle.")
    deposit_received = fields.Boolean(
        string='Deposit Received?',
        default=False,
        copy=False,
        multi='deposit',
        compute='_get_deposit',
        help="True if deposit amount received for current Rental Vehicle.")
    deposit_receipt = fields.Many2one('account.payment', string='Payment Receipt', store=True)
    deposit_return = fields.Boolean(
        string='Deposit Returned?',
        default=False,
        copy=False,
        multi='deposit',
        type='boolean',
        compute='amount_return_compute',
        help="True if deposit amount returned for current Rental Vehicle.")
    contact_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact',
        help="Contact person name.")
    main_cost = fields.Float(
        string='Maintenance Cost',
        default=0.0,
        store=True,
        compute='_total_cost_maint',
        help="insert maintenance cost")
    cost_id = fields.One2many(
        comodel_name='maintenance.cost',
        inverse_name='tenancy',
        string='cost')
    deposit_scheme_type = fields.Selection(
        [('insurance', 'Insurance-based')],
        'Type of Scheme')
    acc_pay_dep_rec_id = fields.Many2one(
        comodel_name='account.voucher',
        string='Account Manager',
        help="Manager of Rental Vehicle.")
    acc_pay_dep_ret_id = fields.Many2one(
        comodel_name='account.voucher',
        string='Account Manager',
        help="Manager of Rental Vehicle.")

    date_start = fields.Datetime(
        string='Start Date',
        default=lambda *a: time.strftime(DT),
        help="Rental Vehicle contract start date .")
    expected_return_date = fields.Datetime(
        compute="_create_date",
        string='Expected Return Date',
        store=True,
        help="Rental Vehicle contract end date.")
    date = fields.Datetime(
        compute="_create_date",
        string='Return Date',
        store=True,
        help="Rental Vehicle contract end date.")
    ref = fields.Char(
        string='Reference',
        default="/")
    # rent_type_id = fields.Many2one(
    #     comodel_name='rent.type',
    #     string='Rent Type')
    total_rent = fields.Float(
        string='Total Rent',
        store=True,
        readonly=True,
        currency_field='currency_id',
        compute='_total_amount_rent',
        help='Total rent of this Rental Vehicle.')
    rent_schedule_ids = fields.One2many(
        comodel_name='tenancy.rent.schedule',
        inverse_name='tenancy_id',
        string='Rent Schedule')
    contract_attachment = fields.Binary(
        string='Rental Contract',
        help='Contract document attachment for selected vehicle')
    cancel_by_id = fields.Many2one('res.users', string="Rent Close By")
    date_cancel = fields.Datetime(string="Rent Close Date")
    account_move_line_ids = fields.One2many(
        comodel_name='account.move.line',
        inverse_name='analytic_account_id',
        string='Entries',
        readonly=True,
        domain=[('display_type', '=', 'product')],
        states={'draft': [('readonly', False)]})
    total_debit_amt = fields.Float(
        string='Total Debit Amount',
        default=0.0,
        compute='_total_debit_amt_calc',
        currency_field='currency_id')
    total_credit_amt = fields.Float(
        string='Total Credit Amount',
        default=0.0,
        compute='_total_credit_amt_calc',
        currency_field='currency_id')
    description = fields.Text(
        string='Description',
        help='Additional Terms and Conditions')
    duration_cover = fields.Text(
        string='Duration of Cover',
        help='Additional Notes')
    total_deb_cre_amt = fields.Float(
        string='Total Expenditure',
        default=0.0,
        compute='_total_deb_cre_amt_calc',
        currency_field='currency_id')
    duration = fields.Integer(string="Duration", default=1, required=True,
                              help="Duration of the rental (in unit of the pricing)")
    duration_unit = fields.Selection([("hour", "Hourly"), ("day", "Daily"), ("week", "Weekly"), ("month", "Monthly")],
                                     string="Unit", required=True, default="day")
    has_outstanding_days = fields.Boolean(compute='_compute_outsatanding_days')
    pricing_id = fields.Many2one(
        'rental.pricing', compute="_compute_pricing",
        string="Pricing", help="Best Pricing Rule based on duration")
    scheduled_invoices_status = fields.Boolean(string="Invoices Status", compute="_compute_scheduled_invoices_status")
    additional_charges = fields.Float(string='Additional Charges', digits=dp.get_precision('Product Price'),
                                      compute='_compute_additional_charges')
    additional_rental_charges_ids = fields.One2many('rental.wizard.fleet.additional.charges', 'agreement_id',
                                                    string='Additional Charges2')
    extra_charges_ids = fields.One2many('rental.wizard.extra.charges', 'agreement_id', string='Extra Charges')
    total_damages_cost = fields.Float(string='Total Damages Amount', currency_field='currency_id')
    additional_mileage_cost = fields.Float(string='Additional Usage Charge', currency_field='currency_id')
    total_other_charges_cost = fields.Float(string='Total Other Charges', currency_field='currency_id')
    additional_day_cost = fields.Float(string='Additional Day Charge', currency_field='currency_id')
    additional_fuel_cost = fields.Float(string='Additional Fuel Cost', currency_field='currency_id')
    additional_drivers_ids = fields.One2many('fleet.additional.drivers', 'rental_id')
    fleet_rental_details = fields.One2many('fleet.rental.vehicle.details', 'rental_contract_id')
    replace_vehicle_details = fields.One2many('replace.vehicle.log', 'replace_id')

    def name_get(self):
        for analytic in self:
            if not analytic.name:
                if analytic.vehicle_id:
                    analytic.write({'name': analytic.vehicle_id.name})
        return super(AccountAnalyticAccount, self).name_get()

    @api.model
    def rent_done_cron(self):
        acc_obj = self.env['account.analytic.account']
        rent_obj = self.env['tenancy.rent.schedule']
        for rec in acc_obj.search([('date', '!=', False),
                                   ('state', '!=', 'close')]):
            records = []
            if rec.rent_schedule_ids:
                records = rent_obj.search([('paid', '=', False),
                                           ('id', 'in',
                                            rec.rent_schedule_ids.ids)])
            if not records:
                if datetime.now() >= datetime.strptime(str(rec.date), DT):
                    reason = "This Rent Order is auto completed due to your rent limit is over."
                    rec.write({'state': 'close',
                               'duration_cover': reason,
                               'date_cancel': datetime.now(),
                               'cancel_by_id': self._uid})
        return True

    # @api.constrains('date_start', 'date')
    # def check_date_overlap(self):
    #     """
    #     This is a constraint method used to check the from date smaller than
    #     the Expiration date.
    #     @param self : object pointer
    #     """
    #     for ver in self:
    #         if ver.date_start and ver.date:
    #             dt_from = datetime.strptime(str(ver.date_start), DT)
    #             dt_to = datetime.strptime(str(ver.date), DT)
    #             if dt_to < dt_from:
    #                 raise ValidationError(
    #                     'Expiration Date Should Be Greater Than Start Date!')

    @api.model
    def default_get(self, fields):
        """
        This method is return if vehicle state is write-off then its
        returns false and if vehicle state is other then its returns true.
        """
        res = super(AccountAnalyticAccount, self).default_get(fields)
        temp = ''
        cr, uid, context, temp = self.env.args
        context = dict(context)
        fleet_obj = self.env['fleet.vehicle']
        if self._context.get('active_id'):
            vehicle_id = fleet_obj.browse(context['active_id'])
            if vehicle_id and vehicle_id.state in ['write-off', 'in_progress']:
                res['vehicle_id'] = False
            # if vehicle_id.state == 'in_progress':
            #     res['vehicle_id'] = False
        return res

    @api.model
    def create(self, vals):
        """
        This Method is used to overrides orm create method,
        to change state and tenant of related property.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        vehicle_id = vals.get('vehicle_id', False)
        st_dt = vals.get('date_start', False)
        vehicle_obj = self.env['fleet.vehicle']
        veh_ser_obj = self.env['fleet.vehicle.log.services']
        vehicle_rec = vehicle_obj.browse(vehicle_id)
        veh_ser_rec = veh_ser_obj.search([('vehicle_id', '=', vehicle_id),
                                          ('date_complete', '>', st_dt)])
        if vehicle_rec.state == 'in_progress' and veh_ser_rec:
            raise ValidationError('This Vehicle In Service. So You Can Not Create Rent Order For This Vehicle.')
        if not vals:
            vals = {}
        if 'tenant_id' in vals:
            vals['ref'] = self.env['ir.sequence'].next_by_code(
                'account.analytic.account')
            vals.update({'is_property': True})
        if 'name' not in vals and 'tenant_id' in vals:
            tenant = self.env['res.partner'].browse(vals['tenant_id']).name
            vals['name'] = tenant + ' - ' + vals['date_start']
        res = super(AccountAnalyticAccount, self).create(vals)
        vehicle_rec.update({'state_id': 11})
        for rent_rec in self:
            # msg1 = ("This is my debug message vals.get('state')! %s",vals)
            # _logger.error(msg1)
            if vals.get('state'):
                if vals['state'] == 'draft':
                    rent_rec.vehicle_id.write({'state': 'booked', 'state_id': 11})
        st_dt = res.date_start
        en_dt = res.date
        veh_id = res.vehicle_id and res.vehicle_id.id or False
        anlytic_obj = self.env['account.analytic.account']
        avilable_records = anlytic_obj.search([('state', '!=', 'close'),
                                               ('vehicle_id', '=', veh_id),
                                               ('id', '!=', res.id)])

        if avilable_records and res.vehicle_id:
            for rec in avilable_records:
                # msg1 = ("This is my debug message rec! %s",rec)
                # _logger.error(msg1)
                if rec.date_start and rec.date:

                    cond1 = (st_dt <= rec.date_start <= en_dt)
                    msg1 = (
                    "This is my debug message st_dt < rec.date_start < en_dt! %s %s %s", st_dt, rec.date_start, en_dt)
                    _logger.error(msg1)
                    cond2 = (st_dt <= rec.date <= en_dt)
                    # msg1 = ("This is my debug message cond2! %s",cond2)
                    # _logger.error(msg1)
                    if cond1 or cond2:
                        raise ValidationError('This vehicle has already been rented.'
                                              'You cannot add the same vehicle multiple times on the same rental date.')
                    else:
                        for rent_rec in self:

                            # msg1 = ("This is my debug message vals.get('state')! %s",vals)
                            # _logger.error(msg1)
                            if vals.get('state'):
                                if vals['state'] == 'draft':
                                    rent_rec.vehicle_id.write({'state': 'booked', 'state_id': 11})

        if not res.sale_order_id and res.tenant_id:
            so_vals = {
                'partner_id': res.tenant_id.id,
                'partner_invoice_id': res.tenant_id.id,
                'partner_shipping_id': res.tenant_id.id,
                'date_order': time.strftime(DT),
                'order_line': [(0, 0, {
                    # 'name': res.vehicle_id.vehicle_prodcut_id.product_template_attribute_value_ids.product_attribute_value_id.name,
                    'name': res.vehicle_id.vehicle_prodcut_id.product_tmpl_id.name,
                    'product_id': res.vehicle_id.vehicle_prodcut_id.id,
                    'product_uom_qty': 1,
                    'product_uom': res.vehicle_id.vehicle_prodcut_id.uom_id.id,
                    'price_unit': res.rent,
                    'tax_id': res.vehicle_id.vehicle_prodcut_id.taxes_id.ids,
                    'duration': res.duration
                })],
                'pricelist_id': self.env.ref('product.list0').id,
                'company_id': res.company_id.id,
            }
            sale_order_id = self.env['sale.order'].create(so_vals)
            res.sale_order_id = sale_order_id.id
            driver_id = res.additional_drivers_ids.additional_driver.id
            if not driver_id:
                raise ValidationError('Please Add Driver Details.')
            # self.env['fleet.vehicle.assignation.log'].create({
            #     'vehicle_id': res.vehicle_id.id,
            #     'driver_id': driver_id,
            #     'date_start': time.strftime(DT)
            # })

        return res

    # @api.multi
    def write(self, vals):
        """
        This Method is used to overrides orm write method,
        to change state and tenant of related property.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        vehicle_id = self.vehicle_id.id
        st_dt = vals.get('date_start', False)
        vehicle_obj = self.env['fleet.vehicle']
        veh_ser_obj = self.env['fleet.vehicle.log.services']
        vehicle_rec = vehicle_obj.browse(vehicle_id)
        veh_ser_rec = veh_ser_obj.search([('vehicle_id', '=', vehicle_id),
                                          ('date_complete', '>', st_dt)])
        if vehicle_rec.state == 'in_progress' and veh_ser_rec:
            raise ValidationError('This Vehicle In Service. So You Can Not Create Rent Order For This Vehicle.')
        rec = super(AccountAnalyticAccount, self).write(vals)
        for rent_rec in self:

            if vals.get('state'):
                if vals['state'] == 'open':
                    rent_rec.vehicle_id.write({
                        'state': 'rent', 'state_id': 9})
                if vals['state'] == 'close':
                    rent_rec.vehicle_id.write(
                        {'state': 'complete', 'state_id': 6})
            st_dt = rent_rec.date_start
            en_dt = rent_rec.date
            veh_id = rent_rec.vehicle_id and rent_rec.vehicle_id.id or False
            anlytic_obj = self.env['account.analytic.account']
            avilable_records = anlytic_obj.search([('state', 'not in', ['close', 'return']),
                                                   ('vehicle_id', '=', veh_id),
                                                   ('id', '!=', rent_rec.id)])
            if avilable_records:
                for record in avilable_records:

                    # msg1 = ("This is my debug message record! %s",record)
                    # _logger.error(msg1)
                    if record.date_start and record.date and record.vehicle_id:
                        cond1 = (st_dt <= record.date_start <= en_dt)
                        # msg1 = ("This is my debug message st_dt < rec.date_start < en_dt! %s %s %s",st_dt,rec.date_start,en_dt)
                        # _logger.error(msg1)
                        cond2 = (st_dt <= record.date <= en_dt)
                        if cond1 or cond2:
                            raise ValidationError('This vehicle is already on rent. '
                                                  'You can not create another rent for this vehicle on same rent date.')
        return rec

    # @api.multi
    def unlink(self):
        raise ValidationError("You can't delete the record")
        """
        Overrides orm unlink method,
        @param self: The object pointer
        @return: True/False.
        """
        rent_ids = []
        for tenancy_rec in self:
            if tenancy_rec.state == 'open':
                raise Warning(
                    _('The Rent Is In-Progress So You Can Not Delete It.'))
            analytic_ids = self.env['account.analytic.line'].search([('account_id', '=', tenancy_rec.id)])
            if analytic_ids and analytic_ids.ids:
                analytic_ids.unlink()
            rent_ids = self.env['tenancy.rent.schedule'].search([('tenancy_id', '=', tenancy_rec.id)])
            post_rent = [x.id for x in rent_ids if x.move_check is True]
            if post_rent:
                raise Warning(
                    _('You cannot delete Tenancy record, if any related Rent Schedule entries are in posted.'))
            else:
                rent_ids.unlink()
            if tenancy_rec.vehicle_id.driver_id and tenancy_rec.vehicle_id.driver_id.id:
                releted_user = tenancy_rec.vehicle_id.driver_id.id
                new_ids = self.env['res.users'].search(
                    [('partner_id', '=', releted_user)])
                if releted_user and new_ids and new_ids.ids:
                    new_ids.write(
                        {'tenant_ids': [(3, tenancy_rec.tenant_id.id)]})
            tenancy_rec.vehicle_id.write(
                {'state': 'inspection', 'current_tenant_id': False, 'state_id': 6})
        return super(AccountAnalyticAccount, self).unlink()

    # @api.multi
    def button_unlock(self):
        """
        This button method is used to Change Tenancy to unlocked.
        @param self: The object pointer
        """
        return self.write({'lock_state': 'open'})

    # @api.multi
    def button_lock(self):
        """
        This button method is used to Change Tenancy to Locked.
        @param self: The object pointer
        """
        return self.write({'lock_state': 'locked'})

    # @api.multi
    def button_rent_schedules(self):
        """
        This button method is used to Change Tenancy state to close.
        @param self: The object pointer
        """
        if not self.scheduled_invoices_status and self.rent_schedule_ids and len(self.rent_schedule_ids) > 0:
            form = "fleet_analytic_accounting.invoice_schedule_warning_form"
            return {
                'name': 'Warning',
                'res_model': 'account.analytic.account',
                'type': 'ir.actions.act_window',
                'view_id': self.env.ref(form).id,
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new'
            }
        else:
            self.create_rent_schedule()

    # @api.multi
    def button_start(self):
        """
        This button method is used to Change Tenancy state to Open.
        @param self: The object pointer
        """
        if self.rent <= 1:
            raise ValidationError("You Can't Enter Rental Vehicle Rent Less Than One(1).")

        if self.tenant_id.tenant and not self.tenant_id.is_driver and not self.additional_drivers_ids:
            raise ValidationError("Please Enter Driver Details.")
        if not self.additional_drivers_ids:
            if self.tenant_id.is_driver:
                line_object = self.env['fleet.additional.drivers']
                new_line = line_object.create({
                    'additional_driver': self.tenant_id.id,
                    'driving_license_number': self.tenant_id.dl_number,
                    'description': self.description
                })
                self.additional_drivers_ids = [(4, new_line.id)]
                self.additional_drivers_ids.flush()

        if self.duration and self.duration_unit:
            unit = self.duration_unit.capitalize() + 's'
            additional_product_obj = self.env['rental.wizard.extra.charges']
            uom_obj = self.env['uom.uom'].search([('name', '=', unit)])
            product_name = self.vehicle_id.vehicle_prodcut_template_id.name + ': ' + (
                'Daily' if unit == 'Days' else self.duration_unit.capitalize()) + ' Rate'
            product_tmpl = self.env['product.template'].search([('name', '=', product_name)])
            rental_pricing = self.env['rental.pricing'].search(
                [('parent_product_template_id', '=', self.vehicle_id.vehicle_prodcut_template_id.id),
                 ('unit', '=', uom_obj.id), ('product_template_id', '=', product_tmpl.id)])
            new_product = self.env['product.product'].search(
                [('product_tmpl_id', '=', rental_pricing.product_template_id.id)])

            value = fields.Datetime.context_timestamp(self, self.date_start).strftime(DT)
            # raise UserError(_('Please add some items to move.'))
            new_additional_product = {'additional_charge_product_id': new_product.id,
                                      'unit_measure': new_product.uom_id.id,
                                      # 'unit_price': rental_pricing.price,
                                      'unit_price': self.rent,
                                      'product_uom_qty': self.duration,
                                      'description': 'Plate No:' + self.vehicle_id.license_plate + ' | Vehicle: ' +
                                                     self.vehicle_id.name + ' | Start Date: ' + str(value) +
                                                     ' | Start Odo.: ' + str(self.odometer) + ' | Start Fuel Lvl: ' +
                                                     str(self.vehicle_id.fuel_level) + ' | Return Odo.: ' + 'TBD' +
                                                     ' | Return Fuel Lvl: ' + 'TBD',
                                      'cost': rental_pricing.price * self.duration,
                                      'agreement_id': self.id}
            additional_product_obj.create(new_additional_product)
            if self.rental_terms == 'spot':
                self.create_rent_schedule()
        rental_number = self.env['ir.sequence'].next_by_code('rental.number')
        prefix = self.rental_terms.split('_')[0].upper()
        if prefix == 'LONG':
            prefix = 'LEASE'
        return self.write({'state': 'hand_over',
                           'rent_entry_chck': False,
                           'name': prefix + '/' + str(rental_number)})

    # @api.multi
    def create_rent_schedule(self):
        """
        This button method is used to create rent schedule Lines.
        @param self: The object pointer
        """
        for tenancy_rec in self:
            for rent_line in tenancy_rec.rent_schedule_ids:
                if rent_line.paid is False and rent_line.move_check is False:
                    raise Warning(
                        _('You can\'t create new rent schedule Please make all related Rent Schedule entries paid.'))
            rent_obj = self.env['tenancy.rent.schedule']
            rent_schedule = False
            if tenancy_rec.date_start and tenancy_rec.duration and tenancy_rec.duration_unit:
                interval = int(tenancy_rec.duration)
                d1 = datetime.strptime(str(tenancy_rec.date_start), DT)
                d2 = datetime.strptime(str(tenancy_rec.date), DT)
                lst_month_inv_date = d1 + relativedelta(months=int(interval))
                if tenancy_rec.invoice_policies == 'advanced':
                    # d1 = d1 + relativedelta(months=int(1))
                    rent_schedule = rent_obj.create({
                        'start_date': d1.strftime(DT),
                        'amount': tenancy_rec.rent + tenancy_rec.additional_charges,
                        'pen_amt': tenancy_rec.rent + tenancy_rec.additional_charges,
                        'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                        'tenancy_id': tenancy_rec.id,
                        'single_inv': True,
                        'currency_id': tenancy_rec.currency_id.id or False,
                        'rel_tenant_id': tenancy_rec.tenant_id.id or False
                    })
                if tenancy_rec.invoice_policies == 'post_invoicing':
                    d2 = d2 + relativedelta(months=int(1))
                    rent_schedule = rent_obj.create({
                        'start_date': d1.strftime(DT),
                        'amount': tenancy_rec.rent + tenancy_rec.additional_charges,
                        'pen_amt': tenancy_rec.rent + tenancy_rec.additional_charges,
                        'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                        'tenancy_id': tenancy_rec.id,
                        'single_inv': True,
                        'currency_id': tenancy_rec.currency_id.id or False,
                        'rel_tenant_id': tenancy_rec.tenant_id.id or False
                    })
                    if rent_schedule:
                        rent_schedule.create_invoice()
                if tenancy_rec.invoice_policies == 'periodic':
                    if tenancy_rec.duration_unit == 'month':
                        closing_date = self.date.date()
                        first_day_of_next_month_closing = date(closing_date.year, closing_date.month, 1)
                        interval = interval + (closing_date != first_day_of_next_month_closing)
                        for i in range(0, interval):
                            d1 = d1 + relativedelta(months=int(1))
                            next_month_start = d1.replace(day=1)
                            if i == 0:
                                rent_schedule = rent_obj.create({
                                    # 'start_date': d1.strftime(DT),
                                    'start_date': next_month_start,
                                    'amount': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'pen_amt': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                                    'tenancy_id': tenancy_rec.id,
                                    'single_inv': True,
                                    'currency_id': tenancy_rec.currency_id.id or False,
                                    'rel_tenant_id': tenancy_rec.tenant_id.id or False
                                })
                            elif i == interval-1:
                                rent_schedule = rent_obj.create({
                                    'start_date': lst_month_inv_date,
                                    'amount': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'pen_amt': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                                    'tenancy_id': tenancy_rec.id,
                                    'currency_id': tenancy_rec.currency_id.id or False,
                                    'rel_tenant_id': tenancy_rec.tenant_id.id or False
                                })

                            else:
                                rent_schedule = rent_obj.create({
                                    'start_date': next_month_start,
                                    'amount': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'pen_amt': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                                    'tenancy_id': tenancy_rec.id,
                                    'currency_id': tenancy_rec.currency_id.id or False,
                                    'rel_tenant_id': tenancy_rec.tenant_id.id or False
                                })
                            if rent_schedule:
                                rent_schedule.create_invoice()
                    # if tenancy_rec.rent_type_id.renttype == 'Years':
                    #     for i in range(0, interval):
                    #         d1 = d1 + relativedelta(years=int(1))
                    #         if i == 0:
                    #             rent_obj.create({
                    #                 'single_inv': True,
                    #                 'start_date': d1.strftime(DT),
                    #                 'amount': tenancy_rec.rent+tenancy_rec.additional_charges,
                    #                 'vehicle_id': tenancy_rec.vehicle_id and
                    #                 tenancy_rec.vehicle_id.id or False,
                    #                 'tenancy_id': tenancy_rec.id,
                    #                 'currency_id': tenancy_rec.currency_id.id or False,
                    #                 'rel_tenant_id': tenancy_rec.tenant_id.id or False
                    #             })
                    #         else:
                    #             rent_obj.create({
                    #                 'start_date': d1.strftime(DT),
                    #                 'amount': tenancy_rec.rent,
                    #                 'vehicle_id': tenancy_rec.vehicle_id and
                    #                 tenancy_rec.vehicle_id.id or False,
                    #                 'tenancy_id': tenancy_rec.id,
                    #                 'currency_id': tenancy_rec.currency_id.id or False,
                    #                 'rel_tenant_id': tenancy_rec.tenant_id.id or False
                    #             })
                    if tenancy_rec.duration_unit == 'week':
                        for i in range(0, interval):
                            d1 = d1 + relativedelta(weeks=int(1))
                            if i == 0:
                                rent_schedule = rent_obj.create({
                                    'single_inv': True,
                                    'start_date': d1.strftime(DT),
                                    'amount': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'pen_amt': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                                    'tenancy_id': tenancy_rec.id,
                                    'currency_id': tenancy_rec.currency_id.id or False,
                                    'rel_tenant_id': tenancy_rec.tenant_id.id or False
                                })
                            else:
                                rent_schedule = rent_obj.create({
                                    'start_date': d1.strftime(DT),
                                    'amount': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'pen_amt': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                    'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                                    'tenancy_id': tenancy_rec.id,
                                    'currency_id': tenancy_rec.currency_id.id or False,
                                    'rel_tenant_id': tenancy_rec.tenant_id.id or False
                                })
                            if rent_schedule:
                                rent_schedule.create_invoice()
                    if tenancy_rec.duration_unit == 'day':
                        rent_schedule = rent_obj.create({
                            'start_date': d1.strftime(DT),
                            'amount': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                            'pen_amt': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                            'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                            'tenancy_id': tenancy_rec.id,
                            'currency_id': tenancy_rec.currency_id.id or False,
                            'rel_tenant_id': tenancy_rec.tenant_id.id or False
                        })
                        if rent_schedule:
                            rent_schedule.create_invoice()
                        # if i == 0:
                        #     rent_obj.create({
                        #         'single_inv': True,
                        #         'start_date': d1.strftime(DT),
                        #         'amount': (tenancy_rec.rent * interval)+tenancy_rec.additional_charges,
                        #         'vehicle_id': tenancy_rec.vehicle_id and
                        #         tenancy_rec.vehicle_id.id or False,
                        #         'tenancy_id': tenancy_rec.id,
                        #         'currency_id': tenancy_rec.currency_id.id or False,
                        #         'rel_tenant_id': tenancy_rec.tenant_id.id or False
                        #     })
                        # else:
                        #     rent_obj.create({
                        #         'start_date': d1.strftime(DT),
                        #         'amount': (tenancy_rec.rent * interval)+tenancy_rec.additional_charges,
                        #         'vehicle_id': tenancy_rec.vehicle_id and
                        #         tenancy_rec.vehicle_id.id or False,
                        #         'tenancy_id': tenancy_rec.id,
                        #         'currency_id': tenancy_rec.currency_id.id or False,
                        #         'rel_tenant_id': tenancy_rec.tenant_id.id or False
                        #     })
                    if tenancy_rec.duration_unit == 'hour':
                        if i == 0:
                            rent_schedule = rent_obj.create({
                                'single_inv': True,
                                'start_date': d1.strftime(DT),
                                'amount': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                'pen_amt': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                                'tenancy_id': tenancy_rec.id,
                                'currency_id': tenancy_rec.currency_id.id or False,
                                'rel_tenant_id': tenancy_rec.tenant_id.id or False
                            })
                        else:
                            rent_schedule = rent_obj.create({
                                'start_date': d1.strftime(DT),
                                'amount': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                'pen_amt': (tenancy_rec.rent + tenancy_rec.additional_charges) / interval,
                                'vehicle_id': tenancy_rec.vehicle_id and tenancy_rec.vehicle_id.id or False,
                                'tenancy_id': tenancy_rec.id,
                                'currency_id': tenancy_rec.currency_id.id or False,
                                'rel_tenant_id': tenancy_rec.tenant_id.id or False
                            })
                        if rent_schedule:
                            rent_schedule.create_invoice()
                tenancy_rec.cr_rent_btn = True
        return True

    # @api.multi
    def button_receive(self):
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
            if tenancy_rec.acc_pay_dep_rec_id and tenancy_rec.acc_pay_dep_rec_id.id:
                acc_pay_form_id = \
                self.env['ir.model.data'].get_object_reference('account', 'view_account_payment_form')[1]
                return {
                    'view_type': 'form',
                    'view_id': acc_pay_form_id,
                    'view_mode': 'form',
                    'res_model': 'account.payment',
                    'res_id': self.acc_pay_dep_rec_id.id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': {
                        'default_partner_id': tenancy_rec.tenant_id.id,
                        'default_partner_type': 'customer',
                        'default_journal_id': jonral_type and jonral_type.ids[0] or False,
                        'default_payment_type': 'inbound',
                        'default_type': 'receipt',
                        'default_communication': 'Deposit Received',
                        'default_tenancy_id': tenancy_rec.id,
                        'default_amount': tenancy_rec.deposit,
                        'default_property_id':
                            tenancy_rec.vehicle_id.id,
                        'close_after_process': True,
                    }
                }
            # if tenancy_rec.deposit == 0.00:
            #     raise Warning(_('Please Enter Advance amount.'))
            # if tenancy_rec.deposit < 0.00:
            #     raise Warning(_('The deposit amount must be strictly positive.'))
            ir_id = self.env['ir.model']._get_id('view_account_payment_form')
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
                    'default_partner_id': tenancy_rec.tenant_id.id,
                    'default_partner_type': 'customer',
                    'default_journal_id': jonral_type and
                                          jonral_type.ids[0] or False,
                    'default_payment_type': 'inbound',
                    'default_type': 'receipt',
                    'default_communication': 'Deposit Received',
                    'default_tenancy_id': tenancy_rec.id,
                    'default_amount': tenancy_rec.deposit,
                    'default_property_id': tenancy_rec.vehicle_id.id,
                    'close_after_process': True,
                }
            }

    # @api.multi
    def button_return(self):
        account_jrnl_obj = self.env['account.journal'].search([('type', '=', 'purchase')])
        if not self.vehicle_id.expence_acc_id.id:
            raise Warning(_('Please Configure Expense Account from Vehicle'))

        inv_line_values = {
            'name': 'Deposit Return' or "",
            # 'origin': 'account.analytic.account' or "",
            'quantity': 1,
            'account_id': self.vehicle_id.expence_acc_id.id or False,
            'price_unit': self.deposit or 0.00,
            'analytic_account_id': self.id or False,
        }
        if self.multi_prop:
            for data in self.prop_id:
                for account in data.property_ids.income_acc_id:
                    account_id = account.id
                inv_line_values.update({'account_id': account_id})

        inv_values = {
            # 'origin': 'Deposit Return For ' + self.name or "",
            'move_type': 'in_invoice',
            # 'property_id': self.vehicle_id.id,
            'partner_id': self.tenant_id.id or False,
            # 'account_id':
            #     self.tenant_id.property_account_payable_id.id or False,
            'invoice_line_ids': [(0, 0, inv_line_values)],
            'date_invoice': datetime.now().strftime(DT) or False,
            'new_tenancy_id': self.id,
            'ref': self.ref,
            'journal_id': account_jrnl_obj and
                          account_jrnl_obj.ids[0] or False,
        }

        acc_id = self.env['account.move'].create(inv_values)
        self.write({'invc_id': acc_id.id})
        wiz_form_id = self.env.ref('account.view_move_form').id
        return {
            'view_type': 'form',
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invc_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': self._context,
        }

    # @api.multi
    def button_set_to_renew(self):
        """
        This Method is used to open Tenancy renew wizard.
        @param self: The object pointer
        @return: Dictionary of values.
        """
        cr, uid, context = self.env.args
        context = dict(context)
        if context is None:
            context = {}
        for tenancy_brw in self:
            tenancy_brw.cr_rent_btn = False
            if tenancy_brw.vehicle_id.state == 'write-off':
                raise Warning(_('You can not renew rent for %s \
                                because this vehicle is in \
                                write-off.') % (tenancy_brw.vehicle_id.name))
            tenancy_rent_ids = self.env['tenancy.rent.schedule'].search(
                [('tenancy_id', '=', tenancy_brw.id),
                 ('move_check', '=', False)])
            if len(tenancy_rent_ids.ids) > 0:
                raise Warning(
                    _('In order to Renew a Tenancy, Please make all related \
                    Rent Schedule entries posted.'))
            date = datetime.strptime(str(tenancy_brw.date), "%Y-%m-%d %H:%M:%S") + timedelta(days=1)
            date1 = datetime.strftime(date, "%Y-%m-%d %H:%M:%S")
            context.update({'edate': date1})
            return {
                'name': 'Tenancy Renew Wizard',
                'res_model': 'renew.tenancy',
                'type': 'ir.actions.act_window',
                'view_id': False,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {'default_start_date': context.get('edate')}
            }

    # @api.multi
    def button_set_to_draft(self):
        """
        This button method is used to Change Tenancy state to close.
        @param self: The object pointer
        """
        for rec in self:
            if rec.state == 'open':
                if rec.rent_schedule_ids:
                    raise Warning(_('You can not set draft stage Because rent schedule is created.'))
            rec.state = 'draft'

    def button_hand_over_vehicle_details(self):

        driver_id = self.additional_drivers_ids.additional_driver.id
        if not driver_id:
            raise ValidationError('Please Add Driver Details.')
        self.env['fleet.vehicle.assignation.log'].create({
            'vehicle_id': self.vehicle_id.id,
            'driver_id': driver_id,
            'date_start': time.strftime(DT)
        })
        """
        This button method is used to Change Tenancy state to close.
        @param self: The object pointer
        """
        fleet_rental_details_obj = self.env['fleet.rental.vehicle.details']

        context = {'default_vehicle_id': self.vehicle_id.id,
                   'default_rental_contract_id': self.id,
                   'default_state': 'hand_over',
                   'default_fuel_level': self.vehicle_id.fuel_level
                   }
        wiz_form_id = self.env.ref('fleet_analytic_accounting.fleet_rental_contract_vehicle_handover_details_wizard').id

        return {
            'name': 'Rent Form New Checking',
            'res_model': 'fleet.rental.vehicle.details',
            'type': 'ir.actions.act_window',
            'context': context,
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new'
        }

    def button_return_vehicle_details(self):
        """
        This button method is used to Change Tenancy state to close.
        @param self: The object pointer
        """

        fleet_rental_details_obj = self.env['fleet.rental.vehicle.details']
        fleet_rental_details = fleet_rental_details_obj.search([('rental_contract_id', '=', self.id),
                                                                ('state', 'in', ['hand_over', 'replacement_handover'])])
        wiz_form_id = self.env.ref('fleet_analytic_accounting.fleet_rental_contract_vehicle_return_details_wizard').id
        context = {'active_model': 'fleet.rental.vehicle.details',
                   'active_id': max(fleet_rental_details.ids),
                   'default_vehicle_id': self.vehicle_id.id,
                   'default_rental_contract_id': self.id,
                   'default_state': 'return',
                   }
        return {
            'name': 'Rent Form New Checking',
            'res_model': 'fleet.rental.vehicle.details',
            'type': 'ir.actions.act_window',
            'context': context,
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new'
        }

    def button_replacement_vehicle_details(self):
        """
        This button method is used to Change Tenancy state to close.
        @param self: The object pointer
        """
        driver_id = self.additional_drivers_ids.additional_driver.id
        fleet_vehicle_assignation_log_obj = self.env['fleet.vehicle.assignation.log'].search([
            ('vehicle_id', '=', self.vehicle_id.id),
            ('driver_id', '=', driver_id),
            ('date_end', '=', False)], limit=1)
        fleet_vehicle_assignation_log_obj.write({
            'date_end': time.strftime(DT)
        })
        fleet_rental_details_obj = self.env['fleet.rental.vehicle.details']
        fleet_rental_details = fleet_rental_details_obj.search([('rental_contract_id', '=', self.id),
                                                                ('vehicle_id', '=', self.vehicle_id.id),
                                                                ('state', 'in', ['hand_over', 'replacement_handover'])])
        wiz_form_id = self.env.ref(
            'fleet_analytic_accounting.fleet_rental_contract_vehicle_replacement_details_wizard').id
        context = {'active_model': 'fleet.rental.vehicle.details',
                   'active_id': max(fleet_rental_details.ids, default=0),
                   'default_vehicle_id': self.vehicle_id.id,
                   'default_rental_contract_id': self.id,
                   'default_state': 'replacement',
                   }
        return {
            'name': 'Rent Form New Checking',
            'res_model': 'fleet.rental.vehicle.details',
            'type': 'ir.actions.act_window',
            'context': context,
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new'
        }

    def button_close_vehicle_details(self):
        """
        This button method is used to Change Tenancy state to close.
        @param self: The object pointer
        """
        driver_id = self.additional_drivers_ids.additional_driver.id
        fleet_vehicle_assignation_log_obj = self.env['fleet.vehicle.assignation.log'].search([
            ('vehicle_id', '=', self.vehicle_id.id),
            ('driver_id', '=', driver_id),
            ('date_end', '=', False)], limit=1)
        fleet_vehicle_assignation_log_obj.write({
            'date_end': time.strftime(DT)
        })

        fleet_rental_details_obj = self.env['fleet.rental.vehicle.details']
        fleet_rental_details = fleet_rental_details_obj.search([('rental_contract_id', '=', self.id),
                                                                ('vehicle_id', '=', self.vehicle_id.id),
                                                                ('state', '=', 'return')])
        wiz_form_id = self.env.ref('fleet_analytic_accounting.fleet_rental_contract_vehicle_close_details_wizard').id
        context = {'active_model': 'fleet.rental.vehicle.details',
                   'active_id': max(fleet_rental_details.ids),
                   'default_vehicle_id': self.vehicle_id.id,
                   'default_rental_contract_id': self.id,
                   'default_state': 'close',
                   }
        return {
            'name': 'Rent Form New Checking',
            'res_model': 'fleet.rental.vehicle.details',
            'type': 'ir.actions.act_window',
            'context': context,
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new'
        }

    @api.model
    def cron_property_states_changed(self):
        """
        This Method is called by Scheduler for change property state
        according to tenancy state.
        @param self: The object pointer
        """
        curr_date = datetime.now().date()
        tncy_ids = self.search([('date_start', '<=', curr_date),
                                ('date', '>=', curr_date),
                                ('state', '=', 'open'),
                                ('is_property', '=', True)])
        if len(tncy_ids.ids) != 0:
            for tncy_data in tncy_ids:
                if tncy_data.property_id and tncy_data.property_id.id:
                    tncy_data.property_id.write(
                        {'state': 'normal', 'color': 7})
        return True

    @api.model
    def cron_property_tenancy(self):
        """
        This Method is called by Scheduler to send email
        to tenant as a reminder for rent payment.
        @param self: The object pointer
        """
        tenancy_ids = []
        due_date = datetime.now().date() + relativedelta(days=7)
        tncy_ids = self.search(
            [('is_property', '=', True), ('state', '=', 'open')])
        for tncy_data in tncy_ids:
            tncy_rent_ids = self.env['tenancy.rent.schedule'].search(
                [('tenancy_id', '=', tncy_data.id),
                 ('start_date', '=', due_date)])
            if tncy_rent_ids and tncy_rent_ids.ids:
                tenancy_ids.append(tncy_data.id)
        tenancy_sort_ids = list(set(tenancy_ids))
        model_data_id = self.env['ir.model.data'].get_object_reference(
            'property_management', 'property_email_template')[1]
        template_brw = self.env['mail.template'].browse(model_data_id)
        for tenancy in tenancy_sort_ids:
            template_brw.send_mail(
                tenancy, force_send=True, raise_exception=False)
        return True

    # @api.multi
    def replace_invoices(self):
        """
        This button method is used to create rent schedule Lines.
        @param self: The object pointer
        """
        if self.duration_unit == 'month' and self.invoice_policies == 'periodic':
            self.create_rent_schedule()
        else:
            for tenancy_rec in self:
                for rent_line in tenancy_rec.rent_schedule_ids:
                    msg1 = "This is my debug message wizard rent_line1! %s", rent_line
                    _logger.error(msg1)
                    rent_line.unlink()
                    msg1 = "This is my debug message wizard rent_line2! %s", rent_line
                    _logger.error(msg1)
            self.create_rent_schedule()


class CustomFleetVehicleAssignationLog(models.Model):
    _inherit = "fleet.vehicle.assignation.log"

    date_start = fields.Datetime(string="Start Date")
    date_end = fields.Datetime(string="End Date")

# @api.multi
# @api.depends('rent_type_id', 'date_start')
# def _create_date(self):
#     for rec in self:
#         if rec.rent_type_id and rec.date_start:
#             if rec.rent_type_id.renttype == 'Months':
#                 rec.date = \
#                     datetime.strptime(rec.date_start, DT) + \
#                     relativedelta(months=int(rec.rent_type_id.duration))
#             if rec.rent_type_id.renttype == 'Years':
#                 rec.date = datetime.strptime(rec.date_start, DT) + \
#                     relativedelta(years=int(rec.rent_type_id.duration))
#             if rec.rent_type_id.renttype == 'Weeks':
#                 rec.date = datetime.strptime(rec.date_start, DT) + \
#                     relativedelta(weeks=int(rec.rent_type_id.duration))
#             if rec.rent_type_id.renttype == 'Days':
#                 rec.date = datetime.strptime(rec.date_start, DT) + \
#                     relativedelta(days=int(rec.rent_type_id.duration))
#             if rec.rent_type_id.renttype == 'Hours':
#                 rec.date = datetime.strptime(rec.date_start, DT) + \
#                     relativedelta(hours=int(rec.rent_type_id.duration))
#     return True
