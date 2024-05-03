from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class RentalProduct(models.Model):
    _inherit = 'product.template'

    rent_ok = fields.Boolean(string="Can be Rented", help="Allow renting of this product.", default=True)
    fleet_ok = fields.Boolean(string="Is Vehicle", help="Enable to create vehicle in fleet module.", default=False)
    accessories_ok = fields.Boolean(string="Accessory", help="Allow if its an accessory", default=False)
    charges_ok = fields.Boolean(string="Charges", help="Allow if its rental charges", default=False)
    detailed_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')], string='Product Type', default='product', required=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')
    reference_product = fields.Many2one('product.template', string='Reference Vehicle')
    category_vehicle_type_id = fields.Many2one('fleet.category.vehicle.type', string='Vehicle Type', required=True)
    category_vehicle_class_id = fields.Many2one('fleet.category.vehicle.class', string='Vehicle Class', required=True)
    category_vehicle_transmission_id = fields.Many2one('fleet.category.vehicle.transmission', string='Transmission',
                                                       required=True)
    category_vehicle_fuel_id = fields.Many2one('fleet.category.vehicle.fuel', string='Fuel', required=True)
    rental_pricing_ids = fields.One2many('rental.pricing', 'parent_product_template_id', string="Rental Pricing",
                                         auto_join=True, copy=True)

    extra_hourly = fields.Float("Extra Hour", help="Fine by hour overdue", company_dependent=True)
    extra_daily = fields.Float("Extra Day", help="Fine by day overdue", company_dependent=True)
    extra_mileage = fields.Float("Extra Mileage Charge", help="Fine by Km overdue", company_dependent=True)
    allowd_daily_mileage = fields.Float("Allowed Daily Mileage(km)", help="Allowed Daily Mileage(km)", default=200)
    allowd_monthly_mileage = fields.Float("Allowed Monthly Mileage(km)", help="Allowed Monthly Mileage(km)",
                                          default=4000)
    # model_id = fields.Many2one("Vehicle Model", 'fleet.vehicle.model')
    # brand_id = fields.Many2one("Vehicle Manufacturer", 'fleet.vehicle.model.brand')
    service_ok = fields.Boolean(string="Is Service", help="Allow if its a service", default=False)

    model_id_zt = fields.Many2one('fleet.vehicle.model', string='Vehicle Model')
    brand_id_zt = fields.Many2one('fleet.vehicle.model.brand', string='Vehicle Manufacturer')

    @api.onchange('service_ok')
    def _onchange_service_ok(self):
        if self.service_ok:
            self.detailed_type = 'service'
        else:
            self.detailed_type = 'product'

    @api.onchange('rent_ok', 'detailed_type')
    def onchange_rent_ok(self):
        if self.rent_ok and self.detailed_type == 'product':
            self.tracking = 'serial'
            self.asset_category_id = False
            self.service_ok = False

    @api.onchange('attribute_line_ids')
    def onchange_fleet_ok(self):
        if self.attribute_line_ids.value_ids.vehicle_model_id:
            for i in self.attribute_line_ids.value_ids.vehicle_model_id:
                i.update({'status': 'used'})

    @api.onchange('accessories_ok')
    def onchange_accessories_ok(self):
        if self.accessories_ok and self.detailed_type == 'product':
            self.fleet_ok = False
            self.service_ok = False

    @api.onchange('fleet_ok')
    def onchange_fleet_ok(self):
        if self.fleet_ok and (self.detailed_type == 'product' or self.detailed_type == 'service'):
            self.accessories_ok = False
            self.service_ok = False

    @api.onchange('service_ok')
    def onchange_service_ok(self):
        if self.service_ok:
            self.accessories_ok = False
            self.sale_ok = False
            self.purchase_ok = False
            self.rent_ok = False
            self.fleet_ok = False
            self.charges_ok = False

    @api.onchange('purchase_ok')
    def onchange_purchase_ok(self):
        if self.purchase_ok:
            self.service_ok = False

    @api.onchange('sale_ok')
    def onchange_sale_ok(self):
        if self.sale_ok:
            self.service_ok = False

    @api.onchange('charges_ok')
    def onchange_charges_ok(self):
        if self.charges_ok:
            self.service_ok = False

    @api.model
    def create(self, vals):
        print('hai')
        if vals.get('accessories_ok'):
            name = vals.get('name')
            if name:
                name_ = name.lower().replace(" ", "")
                existing_record = self.search([('name', 'ilike', name)], limit=1).name
                if existing_record:
                    existing_record_ = existing_record.lower().replace(" ", "")
                    if name_ == existing_record_:
                        raise ValidationError("A record with the same name already exists.")
        res = super(RentalProduct, self).create(vals)
        if res.fleet_ok or res.accessories_ok:
            rental_pricing_obj = self.env['rental.pricing']
            uom_hour = self.env.ref('uom.product_uom_hour')
            uom_day = self.env.ref('uom.product_uom_day')
            uom_week = self.env.ref('fleet_rent.product_uom_week')
            uom_month = self.env.ref('fleet_rent.product_uom_month')
            uom_km = self.env.ref('uom.product_uom_km')
            account_income = self.env.ref('fleet_rent.zt_rac_cri_4005')
            account_expense = self.env.ref('fleet_rent.zt_rac_cri_5005')
            asset_category_id = self.env.ref('fleet_rent.fleet_vehicle_asset_type1')
            additional_products = []
            hourly_product = self.env['product.template'].create({
                'name': res.name + ': Hour Rate',
                'sale_ok': True,
                'purchase_ok': False,
                'fleet_ok': False,
                'rent_ok': False,
                'charges_ok': True,
                'accessories_ok': False,
                'detailed_type': 'service',
                'list_price': 10,
                'uom_id': uom_hour.id,
                'uom_po_id': uom_hour.id,
                'reference_product': res.id,
                'property_account_income_id': account_income.id,
                'property_account_expense_id': account_expense.id,
                'asset_category_id': asset_category_id.id
            })
            daily_product = self.env['product.template'].create({
                'name': res.name + ': Daily Rate',
                'sale_ok': True,
                'purchase_ok': False,
                'rent_ok': False,
                'charges_ok': True,
                'accessories_ok': False,
                'fleet_ok': False,
                'detailed_type': 'service',
                'list_price': 80,
                'uom_id': uom_day.id,
                'uom_po_id': uom_day.id,
                'reference_product': res.id,
                'property_account_income_id': account_income.id,
                'property_account_expense_id': account_expense.id,
                'asset_category_id': asset_category_id.id
            })
            weekly_product = self.env['product.template'].create({
                'name': res.name + ': Week Rate',
                'sale_ok': True,
                'purchase_ok': False,
                'rent_ok': False,
                'fleet_ok': False,
                'charges_ok': True,
                'accessories_ok': False,
                'detailed_type': 'service',
                'list_price': 80,
                'uom_id': uom_week.id,
                'uom_po_id': uom_week.id,
                'reference_product': res.id,
                'property_account_income_id': account_income.id,
                'property_account_expense_id': account_expense.id,
                'asset_category_id': asset_category_id.id
            })
            monthly_product = self.env['product.template'].create({
                'name': res.name + ': Month Rate',
                'sale_ok': True,
                'purchase_ok': False,
                'rent_ok': False,
                'charges_ok': True,
                'accessories_ok': False,
                'fleet_ok': False,
                'detailed_type': 'service',
                'list_price': 80,
                'uom_id': uom_month.id,
                'uom_po_id': uom_month.id,
                'reference_product': res.id,
                'property_account_income_id': account_income.id,
                'property_account_expense_id': account_expense.id,
                'asset_category_id': asset_category_id.id
            })
            extra_day_product = self.env['product.template'].create({
                'name': res.name + ': Extra Day Rate',
                'sale_ok': True,
                'purchase_ok': False,
                'rent_ok': False,
                'fleet_ok': False,
                'charges_ok': True,
                'accessories_ok': False,
                'detailed_type': 'service',
                'list_price': 80,
                'uom_id': uom_day.id,
                'uom_po_id': uom_day.id,
                'reference_product': res.id,
                'property_account_income_id': account_income.id,
                'property_account_expense_id': account_expense.id,
                'asset_category_id': asset_category_id.id
            })
            if res.fleet_ok:
                extra_km_product = self.env['product.template'].create({
                    'name': res.name + ': Extra KM Rate',
                    'sale_ok': True,
                    'purchase_ok': False,
                    'rent_ok': False,
                    'fleet_ok': False,
                    'charges_ok': True,
                    'accessories_ok': False,
                    'detailed_type': 'service',
                    'list_price': 80,
                    'uom_id': uom_km.id,
                    'uom_po_id': uom_km.id,
                    'reference_product': res.id,
                    'property_account_income_id': account_income.id,
                    'property_account_expense_id': account_expense.id,
                    'asset_category_id': asset_category_id.id
                })
                additional_products_extra_km = {
                    'parent_product_template_id': res.id,
                    'product_template_id': extra_km_product.id,
                    'unit': uom_km.id,
                    'price': extra_km_product.list_price,
                    'tax_ids': extra_day_product.taxes_id.ids,
                }
                rental_pricing_obj.create(additional_products_extra_km)
            additional_products_hour = {
                'parent_product_template_id': res.id,
                'product_template_id': hourly_product.id,
                'unit': uom_hour.id,
                'price': hourly_product.list_price,
                'tax_ids': hourly_product.taxes_id.ids,
            }
            rental_pricing_obj.create(additional_products_hour)
            additional_products_day = {
                'parent_product_template_id': res.id,
                'product_template_id': daily_product.id,
                'unit': uom_day.id,
                'price': daily_product.list_price,
                'tax_ids': daily_product.taxes_id.ids,
            }
            rental_pricing_obj.create(additional_products_day)
            additional_products_week = {
                'parent_product_template_id': res.id,
                'product_template_id': weekly_product.id,
                'unit': uom_week.id,
                'price': weekly_product.list_price,
                'tax_ids': weekly_product.taxes_id.ids,
            }
            rental_pricing_obj.create(additional_products_week)
            additional_products_month = {
                'parent_product_template_id': res.id,
                'product_template_id': monthly_product.id,
                'unit': uom_month.id,
                'price': monthly_product.list_price,
                'tax_ids': monthly_product.taxes_id.ids,
            }
            rental_pricing_obj.create(additional_products_month)
            additional_products_extra_day = {
                'parent_product_template_id': res.id,
                'product_template_id': extra_day_product.id,
                'unit': uom_day.id,
                'price': extra_day_product.list_price,
                'tax_ids': extra_day_product.taxes_id.ids,
            }
            rental_pricing_obj.create(additional_products_extra_day)
            if res.fleet_ok:
                if 'brand_id_temp' in vals and 'name' in vals:
                    model_id_obj = self.env['fleet.vehicle.model'].create({
                        'name': res.model_name,
                        'brand_id': res.brand_id_temp.id,
                        'active': True,
                        'vehicle_type': res.vehicle_type,
                        'fuel_tank_capacity': res.fuel_tank_capacity,
                        'category_vehicle_fuel_id': res.category_vehicle_fuel_id.id,
                        'category_vehicle_class_id': res.category_vehicle_class_id.id,
                        'category_vehicle_transmission_id': res.category_vehicle_transmission_id.id,
                        'doors': res.doors,
                        'seats': res.seats
                    })
                    product_temp_obj = self.env['product.template'].search([('model_name', '=', model_id_obj.name),
                                                                            ('brand_id_temp', '=',
                                                                             model_id_obj.brand_id.id)])
                    product_temp_obj.update({
                        'model_id_zt': model_id_obj.id,
                        'brand_id_zt': model_id_obj.brand_id.id
                    })
        else:
            return res
        return res


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    status = fields.Selection([("used", "Available"), ("not_used", "Not Available")], string="Invoicing Policy",
                              required=True, default="not_used")
    fuel_tank_capacity = fields.Integer(string='Fuel Tank Capacity', required=True, default=55)
    category_vehicle_fuel_id = fields.Many2one('fleet.category.vehicle.fuel', string='Fuel', required=True)
    category_vehicle_class_id = fields.Many2one('vehicle.category', string='Vehicle Category', required=True)
    category_vehicle_transmission_id = fields.Many2one('fleet.category.vehicle.transmission', string='Transmission',
                                                       required=True)
    doors = fields.Integer('Doors Number', help='Number of doors of the vehicle', default=4)
    seats = fields.Integer('Seats Number', help='Number of seats of the vehicle', default=5)

    # @api.model
    # def create(self, values):
    #     """Override default Odoo create function and extend."""
    #     res = super(FleetVehicleModel, self).create(values)
    #     model_name = values['name']
    #     brand_name = self.env['fleet.vehicle.model.brand'].browse(values['brand_id'])
    #     attribute_value_name = brand_name.name + ' ' + model_name
    #     attribute_ids = self.env['product.attribute'].search([('name', '=', 'Vehicle Model')])
    #     attribute_value_ids = self.env['product.attribute.value'].search([('name', '=', attribute_value_name)])
    #     if not attribute_ids:
    #         model_attribute = {
    #             'name': 'Vehicle Model',
    #             'create_variant': 'always',
    #             'display_type': 'select'}
    #         product_attribute = self.env['product.attribute']
    #         product_attribute.create(model_attribute)
    #         attribute_ids = self.env['product.attribute'].search([('name', '=', 'Vehicle Model')])
    #     if not attribute_value_ids:
    #         product_attribute_value = self.env['product.attribute.value']
    #         attribute_value_new = {
    #             'name': attribute_value_name,
    #             'attribute_id': attribute_ids.id,
    #             'vehicle_model_id': res.id}
    #         product_attribute_value.create(attribute_value_new)
    #     return res

    @api.model
    def create(self, values):
        """Override default Odoo create function and extend."""
        if values.get('name'):
            vehicle_name = values.get('name').lower().replace(" ", "")
        brand_id = values.get('brand_id')
        fleet_vehicle_model_obj = self.env['fleet.vehicle.model'].search([('brand_id', '=', brand_id)])
        for i in range(len(fleet_vehicle_model_obj)):
            existing_vehicle = fleet_vehicle_model_obj[i].name.lower().replace(" ", "")
            if existing_vehicle == vehicle_name:
                raise ValidationError('Model Name Already Exists with Same Manufacturer')
        res = super(FleetVehicleModel, self).create(values)
        uom_units = self.env.ref('uom.product_uom_unit')
        account_income = self.env.ref('fleet_rent.zt_rac_cri_4005')
        account_expense = self.env.ref('fleet_rent.zt_rac_cri_5005')
        asset_category_id = self.env.ref('fleet_rent.fleet_vehicle_asset_type1')
        name_temp = res.name
        brand_temp = res.brand_id.id
        product_temp_obj_temp = self.env['product.template'].search([('model_name', '=', name_temp),
                                                                     ('brand_id_temp', '=', brand_temp)])
        if not res.id:
            self.env['product.template'].create({
                'name': res.brand_id.name + ' ' + res.name,
                'sale_ok': True,
                'purchase_ok': True,
                'rent_ok': True,
                'fleet_ok': True,
                'charges_ok': False,
                'accessories_ok': False,
                'model_id_zt': res.id,
                'brand_id_zt': res.brand_id.id,
                'detailed_type': 'product',
                'list_price': 0.0,
                'uom_id': uom_units.id,
                'uom_po_id': uom_units.id,
                'supplier_taxes_id': False,
                'tracking': 'serial',
                'property_account_income_id': account_income.id,
                'property_account_expense_id': account_expense.id,
                'asset_category_id': asset_category_id.id
            })
        return res

    # def write(self, values):
    #     """Override default Odoo write function and extend."""
    #     if 'name' in values:
    #         new_name = values['name'].lower().replace(" ", "")
    #         brand_id = self.brand_id.id
    #         existing_models = self.env['fleet.vehicle.model'].search([('brand_id', '=', brand_id)])
    #         for model in existing_models:
    #             if model.name.lower().replace(" ", "") == new_name:
    #                 raise ValidationError('Model Name Already Exists with Same Manufacturer')
    #     return super(FleetVehicleModel, self).write(values)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_in_rent = fields.Float("Quantity currently in rent", compute='_get_qty_in_rent')

    @api.onchange('rent_ok', 'detailed_type')
    def onchange_rent_ok(self):
        if self.rent_ok and self.detailed_type == 'product':
            self.tracking = 'serial'
            self.asset_category_id = False

    def name_get(self):
        res_names = super(ProductProduct, self).name_get()
        if not self._context.get('rental_products'):
            return res_names
        result = []
        rental_product_ids = self.filtered(lambda p: p.rent_ok).ids
        for res in res_names:
            result.append((res[0], res[0] in rental_product_ids and "%s %s" % (res[1], _("(Rental)")) or res[1]))
        return result

    def _get_qty_in_rent_domain(self):
        return [
            ('is_rental', '=', True),
            ('product_id', 'in', self.ids),
            ('state', 'in', ['sale', 'done'])]

    def _get_qty_in_rent(self):
        """
        Note: we don't use product.with_context(location=self.env.company.rental_loc_id.id).qty_available
        because there are no stock moves for services (which can be rented).
        """
        active_rental_lines = self.env['sale.order.line'].read_group(
            domain=self._get_qty_in_rent_domain(),
            fields=['product_id', 'qty_delivered:sum', 'qty_returned:sum'],
            groupby=['product_id'],
        )
        res = dict(
            (data['product_id'][0], data['qty_delivered'] - data['qty_returned']) for data in active_rental_lines)
        for product in self:
            product.qty_in_rent = res.get(product.id, 0)

    def _compute_delay_price(self, duration):
        """Compute daily and hourly delay price.

        :param timedelta duration: datetime representing the delay.
        """
        days = duration.days
        hours = duration.seconds // 3600
        return days * self.extra_daily + hours * self.extra_hourly

    def _get_best_pricing_rule(self, **kwargs):
        """Return the best pricing rule for the given duration.

        :param float duration: duration, in unit uom
        :param str unit: duration unit (hour, day, week)
        :param datetime pickup_date:
        :param datetime return_date:
        :return: least expensive pricing rule for given duration
        :rtype: rental.pricing
        """
        self.ensure_one()
        best_pricing_rule = self.env['rental.pricing']
        # msg1 = ("This is my debug message best_pricing_rule1! %s",best_pricing_rule)
        # _logger.error(msg1)

        if not self.rental_pricing_ids:
            # msg1 = ("This is my debug message best_pricing_rule2! %s",best_pricing_rule)
            # _logger.error(msg1)
            return best_pricing_rule

        pickup_date, return_date = kwargs.get('pickup_date', False), kwargs.get('return_date', False)
        # msg1 = ("This is my debug message pickup_date, return_date! %s %s",pickup_date, return_date)
        # _logger.error(msg1)

        duration, unit = kwargs.get('duration', False), kwargs.get('unit', '')
        # msg1 = ("This is my debug message duration, unit! %s %s",duration, unit)
        # _logger.error(msg1)

        pricelist = kwargs.get('pricelist', self.env['product.pricelist'])
        # msg1 = ("This is my debug message pricelist! %s",pricelist)
        # _logger.error(msg1)

        currency = kwargs.get('currency', self.env.user.company_id.currency_id)
        # msg1 = ("This is my debug message currency! %s ",currency)
        # _logger.error(msg1)

        company = kwargs.get('company', self.env.user.company_id)
        # msg1 = ("This is my debug message company! %s ",company)
        # _logger.error(msg1)

        if pickup_date and return_date:
            duration_dict = self.env['rental.pricing']._compute_duration_vals(pickup_date, return_date)
            # msg1 = ("This is my debug message duration_dict! %s ",duration_dict)
            # _logger.error(msg1)

        elif not (duration and unit):
            return best_pricing_rule  # no valid input to compute duration.

        min_price = float("inf")  # positive infinity
        available_pricings = self.rental_pricing_ids.filtered(
            lambda p: p.pricelist_id == pricelist
        )
        # msg1 = ("This is my debug message available_pricings1! %s ",available_pricings)
        # _logger.error(msg1)

        if not available_pricings:
            # If no pricing is defined for given pricelist:
            # fallback on generic pricings
            available_pricings = self.rental_pricing_ids.filtered(
                lambda p: not p.pricelist_id
            )
            # msg1 = ("This is my debug message available_pricings2! %s ",available_pricings)
            # _logger.error(msg1)
        available_pricings = self.env['rental.pricing'].search(
            [('product_template_id', '=', self.product_tmpl_id.id), ('unit', '=', unit)])
        for pricing in available_pricings:
            if pricing.applies_to(self):
                # msg1 = ("This is my debug message applied pricing! %s ",pricing)
                # _logger.error(msg1)
                if duration and unit:
                    price = pricing._compute_price(duration, unit)
                    # msg1 = ("This is my debug message price1! %s ",price)
                    # _logger.error(msg1)
                else:
                    price = pricing._compute_price(duration_dict[pricing.unit], pricing.unit)
                    # msg1 = ("This is my debug message price2! %s ",price)
                    # _logger.error(msg1)

                if pricing.currency_id != currency:
                    price = pricing.currency_id._convert(
                        from_amount=price,
                        to_currency=currency,
                        company=company,
                        date=date.today(),
                    )

                # msg1 = ("This is my debug message final min_price! %s ",min_price)
                # _logger.error(msg1)
                if price < min_price:
                    min_price, best_pricing_rule = price, pricing

                    # msg1 = ("This is my debug message final min_price, best_pricing_rule! %s %s",min_price, best_pricing_rule)
                    # _logger.error(msg1)

        # msg1 = ("This is my debug message final best_pricing_rule! %s ",best_pricing_rule)
        # _logger.error(msg1)
        return best_pricing_rule

    def action_view_rentals(self):
        """Access Gantt view of rentals (sale.rental.schedule), filtered on variants of the current template."""
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.rental.schedule",
            "name": _("Scheduled Rentals"),
            "views": [[False, "gantt"]],
            'domain': [('product_id', 'in', self.ids)],
            'context': {'search_default_Rentals': 1, 'group_by_no_leaf': 1, 'group_by': [],
                        'restrict_renting_products': True}
        }


class StockLocation(models.Model):
    _inherit = 'stock.location'

    pre_registration = fields.Boolean(string="Pre Registration Location")
