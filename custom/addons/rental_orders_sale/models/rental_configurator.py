from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
import math
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT
from odoo.exceptions import Warning, except_orm, ValidationError
import logging

_logger = logging.getLogger(__name__)


class RentalWizard(models.Model):
    _name = 'rental.wizard'
    _description = 'Configure the rental of a product'

    @api.depends('additional_charges_ids.cost')
    def _compute_additional_charges(self):
        for rec in self:
            charge_total = 0.0
            for line in rec.additional_charges_ids:
                charge_total += line.cost
            rec.update({'additional_charges': charge_total})

    def _default_uom_id(self):
        if self.env.context.get('default_uom_id', False):
            return self.env['uom.uom'].browse(self.context.get('default_uom_id'))
        else:
            return self.env['product.product'].browse(self.env.context.get('default_product_id')).uom_id

    def _default_rental_order_line_id(self):
        if self.env.context.get('default_rental_order_line_id', False):
            return self.env['sale.order.line'].browse(self.context.get('default_rental_order_line_id'))

    # @api.multi
    @api.depends('pickup_date', 'duration', 'duration_unit')
    def _create_date(self):
        for rec in self:
            if rec.pickup_date:
                if rec.duration_unit == 'hour':
                    to_date = \
                        datetime.strptime(datetime.strftime(rec.pickup_date, DT), DT) + \
                        relativedelta(hours=int(rec.duration))
                    rec.return_date = to_date
                if rec.duration_unit == 'day':
                    to_date = \
                        datetime.strptime(datetime.strftime(rec.pickup_date, DT), DT) + \
                        relativedelta(days=int(rec.duration))
                    rec.return_date = to_date
                if rec.duration_unit == 'week':
                    to_date = \
                        datetime.strptime(datetime.strftime(rec.pickup_date, DT), DT) + \
                        relativedelta(weeks=int(rec.duration))
                    rec.return_date = to_date
                if rec.duration_unit == 'month':
                    to_date = \
                        datetime.strptime(datetime.strftime(rec.pickup_date, DT), DT) + \
                        relativedelta(months=int(rec.duration))
                    rec.return_date = to_date
        return True

    rental_order_line_id = fields.Many2one('sale.order.line', ondelete='cascade',
                                           default=_default_rental_order_line_id)
    # When wizard used to edit a Rental SO line
    domain_product_id = fields.Char(string="Product Domain")
    product_id = fields.Many2one(
        'product.product',
        "Product",
        required=True,
        ondelete='cascade',
        help="Product to rent (has to be rentable)",

    )
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True, default=_default_uom_id)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, store=False)

    pickup_date = fields.Datetime(
        string="Pickup", required=True, help="Date of Pickup",
        default=lambda s: datetime.now() + relativedelta(minute=0, second=0, hours=1))

    # return_date = fields.Datetime(
    #     string="Return", required=True, help="Date of Return",
    #     default=lambda s: datetime.now() + relativedelta(minute=0, second=0, hours=1, days=1))

    return_date = fields.Datetime(
        string="Return", required=True, help="Date of Return",
        compute="_create_date")

    quantity = fields.Integer("Quantity", default=1, required=True)  # Can be changed on SO line later if needed

    @api.constrains('quantity')
    def _check_positive_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError("Quantity must be a positive value.")

    pricing_id = fields.Many2one(
        'rental.pricing', compute="_compute_pricing",
        string="Pricing", help="Best Pricing Rule based on duration")
    currency_id = fields.Many2one('res.currency', string="Currency", compute='_compute_displayed_currency')
    rental_type = fields.Selection(
        [('short_term', 'Short Term'),
         ('long_term', 'Long Term'), ('spot', 'Spot Rental'),
         ('online', 'Online Booking')],
        string='Rental Type',
        required=True,
        default='spot', track_visibility='onchange')

    # duration = fields.Integer(
    #     string="Duration", compute="_compute_duration",
    #     help="Duration of the rental (in unit of the pricing)")

    duration = fields.Integer(
        string="Duration", default=1, required=True,
        help="Duration of the rental (in unit of the pricing)")

    # duration_unit = fields.Selection([("hour", "Hours"), ("day", "Days"), ("week", "Weeks"), ("month", "Months")],
    #                                  string="Unit", required=True, compute="_compute_duration")

    duration_unit = fields.Selection([("hour", "Hourly"), ("day", "Daily"), ("week", "Weekly"), ("month", "Monthly")],
                                     string="Unit", required=True, default="day")
    discount_percentage = fields.Float(
        string='Discount (%)',
        digits=(16, 2),
        help='Enter the discount percentage for the product.',
        default=0.0,
        trackvisibility='onchange'
    )
    unit_price = fields.Monetary(
        string="Total Price",
        help="This price is based on the rental price rule that gives the cheapest price for requested duration.",
        readonly=False, default=0.0, required=True)


    price_unit = fields.Monetary(
        string="Basic Price",
        help="This price is based on the rental price rule that gives the cheapest price for requested duration.",
        readonly=True, default=0.0, required=True)

    new_price_unit = fields.Monetary(
        string="Unit Price",
        help="This price is based on the rental price rule that gives the cheapest price for requested duration.",
        readonly=False, default=0.0, required=True,trackvisibility='onchange')

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    additional_charges_ids = fields.One2many('rental.wizard.additional.charges', 'rental_wizard_id',
                                             string='Additional Charges')

    additional_charges = fields.Float(string='Additional Charges', digits=dp.get_precision('Product Price'),
                                      compute='_compute_additional_charges')

    license_plate_no = fields.Many2many('fleet.vehicle', string='License Plate', track_visibility='onchange')

    lot_ids = fields.Many2many(
        'stock.lot',
        string="VIN", help="Only available serial numbers are suggested",
        domain="[('product_id', '=', product_id)]")

    @api.onchange('product_id', 'pickup_date', 'rental_type')
    def set_domain_for_license_plate(self):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        self.license_plate_no = False
        if model == 'sale.order':
            self.rental_type = docs.rental_term
        elif model == 'sale.order.line':
            self.rental_type = docs.order_id.rental_term
        res = {}
        vehicle_list = []
        fleet_obj = self.env['fleet.vehicle']
        domain = [('vehicle_prodcut_id', '=', self.product_id.id)]
        if self.rental_type == 'long_term':
            self.duration_unit = "month"
            domain += [('state_id.name', '!=', 'Sold'), ('state_id.name', '!=', 'Workshop'),
                       ('online_booking', '=', False)]
        else:
            domain += [('state_id.name', '=', 'Available')]
            if self.rental_type == 'online':
                domain += [('online_booking', '=', True)]
            else:
                domain += [('online_booking', '=', False)]
        vehicle_rental = fleet_obj.search(domain)
        if vehicle_rental:
            vehicle_list = vehicle_rental.ids
        res['domain'] = {'license_plate_no': [('id', 'in', vehicle_list)]}
        return res

    @api.onchange('discount_percentage')
    def onchange_discount_percentage(self):
        if self.discount_percentage < 0 or self.discount_percentage > 100:
            raise Warning(_("You cannot apply a discount greater than 0% or less than 100%!!"))
        if self.discount_percentage > 0 or self.discount_percentage == 100:
            self.new_price_unit = (self.price_unit - ((self.discount_percentage * self.price_unit) / 100))
        else:
            self.new_price_unit = self.price_unit

    @api.onchange('new_price_unit')
    def _onchange_new_price_unit(self):
        if self.new_price_unit <= self.price_unit and self.new_price_unit > 0:
            self.discount_percentage = (100 - ((self.new_price_unit * 100) / self.price_unit))
        elif self.new_price_unit > self.price_unit:
            self.discount_percentage = 0.0
        else:
            self.discount_percentage = 100

    @api.onchange('price_unit')
    def new_price_unit_default(self):
        self.new_price_unit = self.price_unit

    @api.onchange('license_plate_no')
    def count_quantity_of_vehicles_opted(self):
        self.quantity = len(self.license_plate_no)

    @api.constrains('pickup_date', 'return_date')
    def _check_pickup_date(self):
        for record in self:
            if record.pickup_date < fields.Datetime.now():
                raise models.ValidationError("Pickup date cannot be in the past.")
            if record.return_date < fields.Datetime.now():
                raise models.ValidationError("Return date cannot be in the past.")

    def _compute_product_id_domain(self):
        domain = [('state_id.name', '=', 'Available')]
        if self.rental_type == 'online':
            domain += [('online_booking', '=', True)]

        vehicle_rental = self.env['fleet.vehicle'].search(domain)
        vehicle_list = [i.vehicle_prodcut_id.id for i in vehicle_rental]

        product_domain = [('id', 'in', vehicle_list)]
        self.domain_product_id = repr(product_domain)  # Store the domain as a string

        return product_domain

    @api.onchange('rental_type')
    def _compute_product_id_domain(self):
        res = {}
        domain = [('state_id.name', '=', 'Available')]
        if self.rental_type == 'online':
            domain += [('online_booking', '=', True)]
        elif self.rental_type == 'long_term':
            domain = []
        elif self.rental_type == 'spot':
            domain += [('online_booking', '=', False)]
        vehicle_rental = self.env['fleet.vehicle'].search(domain)
        vehicle_list = [i.vehicle_prodcut_id.id for i in vehicle_rental]
        product_domain = [('id', 'in', vehicle_list)]
        self.domain_product_id = repr(product_domain)  # Store the domain as a string
        res['domain'] = {'product_id': [('id', 'in', vehicle_list)]}

        return res

    @api.depends('duration_unit', 'duration')
    def _compute_pricing(self):
        self.pricing_id = False
        for wizard in self:
            if wizard.product_id:
                wizard.pricing_id = wizard.product_id._get_best_pricing_rule(
                    unit=wizard.duration_unit,
                    duration=wizard.duration,
                    pricelist=wizard.pricelist_id,
                    company=wizard.company_id)

    @api.depends('pricelist_id', 'pricing_id')
    def _compute_displayed_currency(self):
        for wizard in self:
            wizard.currency_id = wizard.pricelist_id.currency_id or wizard.pricing_id.currency_id

    @api.model
    def create(self, vals):
        anlytic_obj = self.env['account.analytic.account']
        avilable_records = anlytic_obj.search([('state', '!=', 'close'), ('product_id', '=', self.product_id.id)])
        res = super(RentalWizard, self).create(vals)
        product_id = res.product_id
        if avilable_records:
            for record in avilable_records:
                if record.date_start and record.date and record.vehicle_id:
                    cond1 = (res.pickup_date < record.date_start < res.return_date)
                    cond2 = (res.pickup_date < record.date < res.return_date)
                    if cond1 or cond2:
                        if record.vehicle_lot_id:
                            raise ValidationError('These Vehicles are either reserved or currently on rent.')
        return res

    # @api.multi
    def set_rental_order_line(self):
        # if datetime.strptime(str(self.pickup_date), '%Y-%m-%d %H:%M:%S').date() < datetime.now().date():
        #     raise Warning(_('Pick up date should be greater than current date.')) for temporary use
        lot_no = len(self.license_plate_no.ids) if self.license_plate_no.ids else 0
        if lot_no == self.quantity:
            lot_state = 'lot_added'
        else:
            lot_state = 'lot_not_added'
        if self.rental_order_line_id:
            if lot_state == 'lot_added':
                self.rental_order_line_id.lot_state = lot_state
                self.rental_order_line_id.price_unit = self.new_price_unit
                self.rental_order_line_id.duration = self.duration
                self.rental_order_line_id.duration_unit = self.duration_unit
                self.rental_order_line_id.product_id = self.product_id
                self.rental_order_line_id.name = self.product_id.name
                self.rental_order_line_id.product_uom_qty = self.quantity
                self.rental_order_line_id.discount = self.discount_percentage
        else:
            line_obj = self.env['sale.order.line']
            # name = self.product_id.product_tmpl_id.brand_id.name + ' ' + self.product_id.product_tmpl_id.model_id.name
            name = self.product_id.product_tmpl_id.name
            new_line = line_obj.create({
                'product_id': self.product_id.id,
                'name': name,
                'price_unit': self.new_price_unit,
                'product_uom_qty': self.quantity,
                'product_uom': self.product_id.uom_id.id,
                'pickup_date': self.pickup_date,
                'tax_id': self.product_id.taxes_id.ids,
                'return_date': self.return_date,
                'rental_wizard_id': self.id,
                'is_rental': True,
                'duration': self.duration,
                'duration_unit': self.duration_unit,
                'lot_state': lot_state,
                'discount': self.discount_percentage,
                'order_id': self.rental_order_line_id.order_id.id if self.rental_order_line_id.order_id else self.env.context.get('active_ids')[0]})
            self.rental_order_line_id = new_line
            new_line._compute_amount()
            return True
        return True

    @api.depends('pricing_id', 'pickup_date', 'return_date')
    def _compute_duration(self):
        for wizard in self:
            values = {
                'duration_unit': 'day',
                'duration': 1.0,
            }
            if wizard.pickup_date and wizard.return_date:
                duration_dict = self.env['rental.pricing']._compute_duration_vals(wizard.pickup_date,
                                                                                  wizard.return_date)
                if wizard.pricing_id:
                    # msg1 = ("This is my debug message wizard.pricing_id! %s",wizard.pricing_id)
                    # _logger.error(msg1)
                    values = {
                        'duration_unit': wizard.pricing_id.unit,
                        'duration': duration_dict[wizard.pricing_id.unit]
                    }
                    # msg1 = ("This is my debug message rental_order_line_id! %s",self.rental_order_line_id)
                    # _logger.error(msg1)
                else:
                    values = {
                        'duration_unit': 'day',
                        'duration': duration_dict['day']
                    }
                    # msg1 = ("This is my debug message wizard.values! %s",values)
                    # _logger.error(msg1)
            wizard.update(values)

    @api.onchange('pricing_id', 'currency_id', 'duration', 'duration_unit', 'additional_charges', 'product_id','new_price_unit')
    def _compute_unit_price(self):
        for wizard in self:
            if wizard.pricing_id and wizard.duration > 0:
                unit_price = wizard.pricing_id._compute_price(wizard.duration,
                                                              wizard.duration_unit) + wizard.additional_charges
                if wizard.currency_id != wizard.pricing_id.currency_id:
                    wizard.unit_price = wizard.pricing_id.currency_id._convert(
                        from_amount=unit_price,
                        to_currency=wizard.currency_id,
                        company=wizard.company_id,
                        date=date.today())
                    wizard.new_price_unit = wizard.unit_price / wizard.duration
                else:
                    wizard.unit_price = unit_price
                    wizard.new_price_unit = wizard.unit_price / wizard.duration
            elif wizard.duration > 0:
                if self.duration_unit and self.product_id:
                    duration_unit = self.duration_unit.capitalize() + 's'
                    unit_obj = self.env['uom.uom'].search([('name', '=', duration_unit)])
                    product_name = self.product_id.product_tmpl_id.name + ': ' + (
                        'Daily' if duration_unit == 'Days' else self.duration_unit.capitalize()) + ' Rate'
                    product_tmpl = self.env['product.template'].search([('name', '=', product_name)])
                    available_pricing = self.env['rental.pricing'].search(
                        [('parent_product_template_id', '=', self.product_id.product_tmpl_id.id),
                         ('unit', '=', unit_obj.id), ('product_template_id', '=', product_tmpl.id)])
                    wizard.price_unit = available_pricing.price
                    wizard.unit_price = wizard.new_price_unit * wizard.duration
            # line_obj = self.env['sale.order.line'].search([('id', '=', self.rental_order_line_id.id)])
            # msg1 = ("This is my debug message wizard line_obj1! %s",line_obj)
            # _logger.error(msg1)
            # line_obj.write({
            #     'price_unit':self.unit_price,
            #     'product_uom_qty':self.quantity,
            #     'pickup_date':self.pickup_date,
            #     'return_date':self.return_date,
            #     'is_rental':True})

    # @api.model
    # def create(self, vals):
    #     #rec = super(RentalWizard, self).create(vals)
    #     line_obj = self.env['sale.order.line']
    #     line_obj_val = line_obj.search([('id', '=', vals['rental_order_line_id'])])
    #     msg1 = ("This is my debug message line_obj %s",line_obj)
    #     _logger.error(msg1)
    #     msg1 = ("This is my debug message line_obj_val! %s",line_obj_val)
    #     _logger.error(msg1)
    #     # if line_obj_val:
    #     #     msg1 = ("This is my debug message wizard check5! ")
    #     #     _logger.error(msg1)
    #     #     rec = super(RentalWizard, self).update(vals)
    #     # else:
    #     msg1 = ("This is my debug message wizard check6! ")
    #     _logger.error(msg1)
    #     rec = super(RentalWizard, self).create(vals)
    #     return rec

    # @api.depends('unit_price', 'pricing_id')
    # def _compute_pricing_explanation(self):
    #     translated_pricing_duration_unit = dict()
    #     for key, value in self.pricing_id._fields['unit']._description_selection(self.env):
    #         translated_pricing_duration_unit[key] = value
    #     for wizard in self:
    #         if wizard.pricing_id and wizard.duration > 0 and wizard.unit_price != 0.0:
    #             if wizard.pricing_id.duration > 0:
    #                 pricing_explanation = "%i * %i %s (%s)" % (
    #                     math.ceil(wizard.duration / wizard.pricing_id.duration),
    #                     wizard.pricing_id.duration,
    #                     translated_pricing_duration_unit[wizard.pricing_id.unit],
    #                     self.env['ir.qweb.field.monetary'].value_to_html(
    #                         wizard.pricing_id.price, {
    #                             'from_currency': wizard.pricing_id.currency_id,
    #                             'display_currency': wizard.pricing_id.currency_id,
    #                             'company_id': self.env.company.id,
    #                         }))
    #             else:
    #                 pricing_explanation = _("Fixed rental price")
    #             if wizard.product_id.extra_hourly or wizard.product_id.extra_daily:
    #                 pricing_explanation += "<br/>%s" % (_("Extras:"))
    #             if wizard.product_id.extra_hourly:
    #                 pricing_explanation += " %s%s" % (
    #                     self.env['ir.qweb.field.monetary'].value_to_html(
    #                         wizard.product_id.extra_hourly, {
    #                             'from_currency': wizard.product_id.currency_id,
    #                             'display_currency': wizard.product_id.currency_id,
    #                             'company_id': self.env.company.id,
    #                         }),
    #                     _("/hour"))
    #             if wizard.product_id.extra_daily:
    #                 pricing_explanation += " %s%s" % (
    #                     self.env['ir.qweb.field.monetary'].value_to_html(
    #                         wizard.product_id.extra_daily, {
    #                             'from_currency': wizard.product_id.currency_id,
    #                             'display_currency': wizard.product_id.currency_id,
    #                             'company_id': self.env.company.id,
    #                         }),
    #                     _("/day"))
    #             wizard.pricing_explanation = pricing_explanation
    #         else:
    #             # if no pricing on product: explain only sales price is applied ?
    #             if not wizard.product_id.rental_pricing_ids and wizard.duration:
    #                 wizard.pricing_explanation = _("No rental price is defined on the product.\nThe price used is the sales price.")
    #             else:
    #                 wizard.pricing_explanation = ""

    # _sql_constraints = [
    #     ('rental_period_coherence',
    #         "CHECK(pickup_date < return_date)",
    #         "Please choose a return date that is after the pickup date."),
    # ]

    # _sql_constraints = [
    #     ('rental_period_coherence',
    #         "CHECK(1=1)",
    #         "Please choose a return date that is after the pickup date."),
    # ]

class RentalWizardAdditionalCharges(models.Model):
    _name = 'rental.wizard.additional.charges'

    # def _compute_additional_charges_values(self):
    #     for rec in self:
    #         charge_total = 0.0
    #         for line in rec.additional_charges_ids:
    #              charge_total += line.cost
    #         rec.update({'additional_charges': charge_total })

    @api.onchange('additional_charge_product_id')
    def _compute_pricing(self):
        self.pricing_id = False
        for wizard in self:
            if wizard.additional_charge_product_id:
                wizard.pricing_id = wizard.additional_charge_product_id._get_best_pricing_rule(
                    unit=wizard.duration_unit,
                    duration=wizard.duration,
                    pricelist=wizard.pricelist_id,
                    company=wizard.company_id)

    @api.onchange('pricing_id')
    def _compute_unit_price(self):
        for wizard in self:
            if wizard.pricing_id and wizard.duration > 0:
                unit_price = wizard.pricing_id._compute_price(wizard.duration, wizard.duration_unit)
                # msg1 = ("This is my debug message unit_price! %s ",unit_price)
                # _logger.error(msg1)
                wizard.cost = unit_price

    additional_charge_product_id = fields.Many2one('product.product', string='Product', required=True)

    rental_wizard_id = fields.Many2one('rental.wizard', string='Rental wizard')

    cost = fields.Float(string='Cost', digits=dp.get_precision('Product Price'), required=True)

    quantity = fields.Float("Quantity", default=lambda self: self.env.context.get('default_quantity'),
                            required=True)

    pricing_id = fields.Many2one(
        'rental.pricing', string="Pricing", help="Best Pricing Rule based on duration")

    duration = fields.Integer(string="Duration", default=lambda self: self.env.context.get('default_duration'),
                              required=True)

    duration_unit = fields.Selection([("hour", "Hours"), ("day", "Days"), ("week", "Weeks"), ("month", "Months")],
                                     string="Unit",
                                     default=lambda self: self.env.context.get('default_duration_unit'),
                                     required=True)

    pickup_date = fields.Datetime(
        string="Pickup", required=True, help="Date of Pickup",
        default=lambda self: self.env.context.get('default_pickup_date'))

    return_date = fields.Datetime(
        string="Return", required=True, help="Date of Return",
        default=lambda self: self.env.context.get('default_return_date'))

    # currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.context.get('default_currency_id'))

    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, store=False)

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    lot_ids = fields.Many2many(
        'stock.lot',
        string="VIN", help="Only available serial numbers are suggested",
        domain="[('product_id', '=', additional_charge_product_id)]")

    # additional_charge_product_id = fields.Many2one('product.product',string='Product')
    # rental_wizard_id = fields.Many2one('rental.wizard',string='Rental wizard')
    # cost = fields.Float(string='Cost', digits=dp.get_precision('Product Price'))
    # quantity = fields.Float("Quantity",compute='_compute_additional_charges_values', required=True)
    # pricing_id = fields.Many2one('rental.pricing', compute='_compute_additional_charges_values',string="Pricing")