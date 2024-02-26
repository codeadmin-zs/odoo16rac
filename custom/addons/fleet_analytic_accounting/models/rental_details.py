from odoo import models, fields, _, api
from datetime import datetime, date
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DT
from dateutil.relativedelta import relativedelta
import logging
from dateutil import tz
import time

_logger = logging.getLogger(__name__)

class RentalContractDetails(models.Model):
    _name = 'fleet.rental.vehicle.details'

    def compute_total_extra_day_usage(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        if self.state == 'return' or self.state == 'replacement' or self.state == 'replacement_return':
            if self.rental_contract_id.date_start > self.date:
                raise ValidationError('Return Date Should Be Greater Than Handover Date.')
            expected_return_date = self.rental_contract_id.date.date()
            returned_date = self.date.date()
            duration_in_days = (returned_date - self.rental_contract_id.ten_date.date()).days
            time_difference = self.date - self.rental_contract_id.ten_date
            days_daily_calc = time_difference.days
            hours_daily_calc = time_difference.seconds // 3600
            buffer_hours = self.env['buffer.hours'].search([], limit=1).hours
            flag = False
            if hours_daily_calc > buffer_hours:
                duration_in_days += 1
                flag = True
            else:
                duration_in_days = days_daily_calc
            additional_day_cost = 0.0
            additional_product_obj = self.env['rental.wizard.extra.charges']
            if expected_return_date < returned_date or flag == True:
                uom_obj = self.env['uom.uom'].search([('name', '=', 'Days')])
                product_name = self.vehicle_id.vehicle_prodcut_template_id.name + ': Extra Day Rate'
                product_tmpl = self.env['product.template'].search([('name', '=', product_name)])
                rental_pricing = self.env['rental.pricing'].search(
                    [('parent_product_template_id', '=', self.vehicle_id.vehicle_prodcut_template_id.id),
                     ('unit', '=', uom_obj.id), ('product_template_id', '=', product_tmpl.id)])
                new_product = self.env['product.product'].search(
                    [('product_tmpl_id', '=', rental_pricing.product_template_id.id)])
                extra_days = (returned_date - expected_return_date).days
                if hours_daily_calc > buffer_hours:
                    extra_days += 1

                uom_name = 'Weeks' if 6 <= extra_days <= 20 else ('Days' if extra_days < 6 else 'Months')
                uom = self.env['uom.uom'].search([('name', '=', uom_name)])
                rate_suffix = ': Week Rate' if uom_name == 'Weeks' else (
                    ': Month Rate' if uom_name == 'Months' else ': Daily Rate')
                pro = self.vehicle_id.vehicle_prodcut_template_id.name + rate_suffix
                pro_tmpl = self.env['product.template'].search([('name', '=', pro)])
                rent = self.env['rental.pricing'].search([
                    ('parent_product_template_id', '=', self.vehicle_id.vehicle_prodcut_template_id.id),
                    ('unit', '=', uom.id),
                    ('product_template_id', '=', pro_tmpl.id)
                ])
                new_pro = self.env['product.product'].search([
                    ('product_tmpl_id', '=', rent.product_template_id.id)
                ])
                if self.state == 'replacement' or self.state == 'replacement_return':
                    unit_price = self.rental_contract_id.rent / 6 if uom_name == 'Weeks' else (
                        self.rental_contract_id.rent / 20 if uom_name == 'Months' else self.rental_contract_id.rent)
                else:
                    unit_price = new_pro.lst_price / 6 if uom_name == 'Weeks' else (
                        new_pro.lst_price / 20 if uom_name == 'Months' else new_pro.lst_price)
                additional_day_cost = unit_price * extra_days

                new_additional_product = {'additional_charge_product_id': new_product.id,
                                          'unit_measure': new_product.uom_id.id,
                                          'unit_price': unit_price,
                                          'description': 'Extra Days - ' + str(extra_days) + ' | Plate No: '
                                                         + self.vehicle_id.license_plate,
                                          'product_uom_qty': abs(extra_days),
                                          'cost': additional_day_cost,
                                          'agreement_id': self.rental_contract_id.id
                                          }

                exist = False
                for each in self.rental_contract_id.extra_charges_ids:
                    if each.additional_charge_product_id.id != new_product.id:
                        exist = False
                    else:
                        if each.product_uom_qty != extra_days:
                            each.write({'product_uom_qty': extra_days,
                                        'cost': additional_day_cost})
                            exist = False
                        else:
                            exist = True
                if not exist:
                    new_product = additional_product_obj.create(new_additional_product)
                    # if self.rental_contract_id.rental_terms == 'spot':
                    self.create_move_lines(new_product)

            self.additional_day_cost = additional_day_cost
            self.rental_contract_id.additional_day_cost = additional_day_cost

    @api.constrains('odometer')
    def _check_positive_odometer(self):
        if self.state == 'return':
            print(self.rental_contract_id.current_odometer)
            for record in self:
                if record.odometer <= self.rental_contract_id.current_odometer:
                    raise ValidationError("Odometer should be greater than the Last Odometer value..")

    def compute_total_extra_mileage_usage(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        if self.state == 'hand_over' and self.rental_contract_id.rental_terms == 'spot':
            tenancy_rent_schedule_obj = self.env['tenancy.rent.schedule']
            tenancy_rent_schedule_items = tenancy_rent_schedule_obj.search(
                [('tenancy_id', '=', self.rental_contract_id.id)])
            desc_start = tenancy_rent_schedule_items.invc_id.invoice_line_ids[0].description.split(' | Start Odo.: ')[0]
            desc_end = tenancy_rent_schedule_items.invc_id.invoice_line_ids[0].description.split(' | Start Fuel Lvl: ')[1]
            tenancy_rent_schedule_items.invc_id.invoice_line_ids[0].write({'description': desc_start +
                                                                           ' | Start Odo.: ' + str(self.odometer) +
                                                                           ' | Start Fuel Lvl: ' + desc_end})
        if self.state == 'return' or self.state == 'replacement' or self.state == 'replacement_return':
            tenancy_starting_odometer = self.rental_contract_id.current_odometer_temp
            allowed_mileage_per_day = self.vehicle_id.vehicle_prodcut_template_id.allowd_daily_mileage
            allowed_mileage_per_month = self.vehicle_id.vehicle_prodcut_template_id.allowd_monthly_mileage
            tenancy_start_date = datetime.strptime(str(self.rental_contract_id.date_start), '%Y-%m-%d %H:%M:%S')
            tenancy_expiry_date = datetime.strptime(str(self.rental_contract_id.date), '%Y-%m-%d %H:%M:%S')
            contract_duration_in_days = (tenancy_expiry_date - tenancy_start_date).days
            delta = relativedelta(tenancy_expiry_date, tenancy_start_date)
            contract_duration_in_months = delta.years * 12 + delta.months
            if self.rental_contract_id.rental_terms == 'long_term':
                total_allowed_mileage_for_contract = contract_duration_in_months * allowed_mileage_per_month
            else:
                total_allowed_mileage_for_contract = contract_duration_in_days * allowed_mileage_per_day
            additional_mileage_in_km = 0
            additional_mileage_cost = 0
            total_mileages = self.odometer - tenancy_starting_odometer
            additional_product_obj = self.env['rental.wizard.extra.charges']
            if total_mileages > total_allowed_mileage_for_contract:
                additional_mileage_in_km = total_mileages - total_allowed_mileage_for_contract
                uom_obj = self.env['uom.uom'].search([('name', '=', 'km')])
                if self.vehicle_id.name != self.rental_contract_id.vehicle_id_temp.name:
                    rental_pricing = self.env['rental.pricing'].search([('parent_product_template_id', '=',
                                                                       self.rental_contract_id.vehicle_id_temp.vehicle_prodcut_template_id.id),
                                                                      ('unit', '=', uom_obj.id)])
                    new_product = self.env['product.product'].search(
                        [('product_tmpl_id', '=', rental_pricing.product_template_id.id)])
                    additional_mileage_cost = additional_mileage_in_km * new_product.lst_price
                else:
                    rental_pricing = self.env['rental.pricing'].search(
                        [('parent_product_template_id', '=', self.vehicle_id.vehicle_prodcut_template_id.id),
                        ('unit', '=', uom_obj.id)])
                    new_product = self.env['product.product'].search(
                        [('product_tmpl_id', '=', rental_pricing.product_template_id.id)])
                    additional_mileage_cost = additional_mileage_in_km * new_product.lst_price
                new_additional_product = {'additional_charge_product_id': new_product.id,
                                          'unit_measure': new_product.uom_id.id,
                                          'unit_price': new_product.lst_price,
                                          'description': 'Plate No: ' + self.vehicle_id.license_plate +
                                                         ' | Additional KMs Used -' +
                                                         (self.vehicle_id.license_plate if self.state == 'replacement' else '')
                                                         + str(additional_mileage_in_km),
                                          'product_uom_qty': additional_mileage_in_km,
                                          'cost': additional_mileage_cost,
                                          'agreement_id': self.rental_contract_id.id}
                exist = False
                for each in self.rental_contract_id.extra_charges_ids:
                    if each.additional_charge_product_id.id != new_product.id:
                        exist = False
                    else:
                        if each.product_uom_qty != additional_mileage_in_km:
                            each.write({'product_uom_qty': additional_mileage_in_km,
                                        'cost': additional_mileage_cost})
                            exist = False
                        else:
                            exist = True
                if not exist:
                    new_product = additional_product_obj.create(new_additional_product)
                    # if self.rental_contract_id.rental_terms == 'spot':
                    self.create_move_lines(new_product)
            self.additional_mileage_cost = additional_mileage_cost
            self.rental_contract_id.additional_mileage_cost = additional_mileage_cost

    def computing_extra_fuel_cost(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        if self.state == 'hand_over' and self.rental_contract_id.rental_terms == 'spot':
            tenancy_rent_schedule_obj = self.env['tenancy.rent.schedule']
            tenancy_rent_schedule_items = tenancy_rent_schedule_obj.search(
                [('tenancy_id', '=', self.rental_contract_id.id)])
            desc_start = tenancy_rent_schedule_items.invc_id.invoice_line_ids[0].description.split(' | Start Fuel Lvl: ')[0]
            desc_end = tenancy_rent_schedule_items.invc_id.invoice_line_ids[0].description.split(' | Return Odo.: ')[1]
            tenancy_rent_schedule_items.invc_id.invoice_line_ids[0].write({'description': desc_start +
                                                                           ' | Start Fuel Lvl: ' + str(self.fuel_level) +
                                                                           ' | Return Odo.: ' + desc_end})
        if self.state == 'return' or self.state == 'replacement':
            current_fuel_level = int(self.fuel_level)
            fuel_level_at_handover = int(self.rental_contract_id.fuel_level_temp)
            additional_fuel_cost = 0
            acc = []
            if current_fuel_level < fuel_level_at_handover:
                additional_product_obj = self.env['rental.wizard.extra.charges']
                fuel = self.vehicle_id.model_id.category_vehicle_fuel_id
                new_product_template = self.env['product.template'].search([('charges_ok', '=', True),
                                                                            ('name', '=', 'Fuel: ' + fuel.name)]).id
                new_product = self.env['product.product'].search([('product_tmpl_id', '=', new_product_template)])
                # new_product = self.env.ref('fleet_rent.additional_charge_extra_days').product_variant_id
                fuel_rate = new_product.lst_price
                fuel_tank_capacity = self.vehicle_id.model_id.fuel_tank_capacity / 8
                extra_fuels_used = (fuel_level_at_handover - current_fuel_level) * fuel_tank_capacity
                additional_fuel_cost = fuel_rate * extra_fuels_used
                new_additional_product = {'additional_charge_product_id': new_product.id,
                                          'unit_measure': new_product.uom_id.id,
                                          'unit_price': new_product.lst_price,
                                          'description': 'Plate No: ' + self.vehicle_id.license_plate +
                                                         ' | Additional Fuels Used -' +
                                                         (self.vehicle_id.license_plate if self.state == 'replacement' else ' ')
                                                         + str(extra_fuels_used),
                                          'product_uom_qty': extra_fuels_used,
                                          'cost': additional_fuel_cost,
                                          'agreement_id': self.rental_contract_id.id}
                exist = False
                for each in self.rental_contract_id.extra_charges_ids:
                    if each.additional_charge_product_id.id != new_product.id:
                        exist = False
                    else:
                        if each.product_uom_qty != extra_fuels_used:
                            each.write({'product_uom_qty': extra_fuels_used,
                                        'cost': additional_fuel_cost})
                            exist = False
                        else:
                            exist = True
                if not exist:
                    new_product = additional_product_obj.create(new_additional_product)
                    # if self.rental_contract_id.rental_terms == 'spot':
                    self.create_move_lines(new_product)
            self.additional_fuel_cost = additional_fuel_cost
            self.rental_contract_id.additional_fuel_cost = additional_fuel_cost

    @api.onchange('hood_dent_cost', 'front_r_door_dent_cost', 'front_l_door_dent_cost', 'back_r_door_dent_cost',
                  'back_l_door_dent_cost',
                  'boot_dent_cost', 'hood_scratch_cost', 'hood_scratch_cost', 'front_r_door_scratch_cost',
                  'front_l_door_scratch_cost',
                  'back_r_door_scratch_cost', 'back_l_door_scratch_cost', 'boot_scratch_cost')
    def compute_total_damages_cost(self):
        # if self.state == 'return' or self.state == 'replacement':
        total_dent_cost = self.hood_dent_cost + self.front_r_door_dent_cost + self.front_l_door_dent_cost + \
                self.back_r_door_dent_cost + self.back_l_door_dent_cost + self.boot_dent_cost
        total_scratch_cost = self.hood_scratch_cost + self.front_r_door_scratch_cost + self.boot_scratch_cost + \
                                 self.front_l_door_scratch_cost + self.back_r_door_scratch_cost + self.back_l_door_scratch_cost
        total_damages_cost = total_dent_cost + total_scratch_cost
        self.total_damages_cost = total_damages_cost

        # self.total_damages_cost = _total_damages_cost
        # for record in self:
        #     record.total_damages_cost = _total_damages_cost


            # self.rental_contract_id.total_damages_cost = total_damages_cost

            # additional_product_obj = self.env['rental.wizard.extra.charges']
            # if total_dent_cost > 0:
            #     new_product = self.env.ref('fleet_rent.additional_charge_dents').product_variant_id
            #     new_additional_product = {'additional_charge_product_id': new_product.id,
            #                               'unit_measure': new_product.uom_id.id,
            #                               'unit_price': total_dent_cost,
            #                               'description': '',
            #                               'product_uom_qty': 1,
            #                               'cost': total_dent_cost,
            #                               'agreement_id': self.rental_contract_id.id}
            #     new_product = additional_product_obj.create(new_additional_product)
            #     # if self.rental_contract_id.rental_terms == 'spot':
            #     self.create_move_lines(new_product)
            # if total_scratch_cost > 0:
            #     new_product = self.env.ref('fleet_rent.additional_charge_scratches').product_variant_id
            #     new_additional_product = {'additional_charge_product_id': new_product.id,
            #                               'unit_measure': new_product.uom_id.id,
            #                               'unit_price': total_dent_cost,
            #                               'description': '',
            #                               'product_uom_qty': 1,
            #                               'cost': total_dent_cost,
            #                               'agreement_id': self.rental_contract_id.id}
            #     new_product = additional_product_obj.create(new_additional_product)
            #                     # if self.rental_contract_id.rental_terms == ' spot':
            #     self.create_move_lines(new_product)

    @api.onchange('vehicle_id')
    def replacement_vehicle_checking(self):
        if self.state == 'replacement':
            anlytic_obj = self.env['account.analytic.account']
            avilable_records = anlytic_obj.search(['|', ('state', '!=', 'close'), '|',
                                                   ('date_start', '>=', self.rental_contract_id.date_start),
                                                   ('date_start', '>=', self.rental_contract_id.date), '|',
                                                   ('date', '>=', self.rental_contract_id.date_start),
                                                   ('date', '>=', self.rental_contract_id.date),
                                                   ('id', '!=', self.rental_contract_id.id)])
            msg1 = ("This is my debug message avilable_records')! %s", avilable_records)
            _logger.error(msg1)
            vehicle_list = []
            if avilable_records:
                for record in avilable_records:
                    if record.date_start and record.date and record.vehicle_id:
                        cond1 = (self.rental_contract_id.date_start <= record.date_start <= self.rental_contract_id.date)
                        cond2 = (self.rental_contract_id.date_start <= record.date <= self.rental_contract_id.date)
                        # if (cond1 or cond2) and record.vehicle_id != self.vehicle_id:
                        #  # vehicle_list.append(record.vehicle_id.id)
            fleet_obj = self.env['fleet.vehicle'].search([('state_id', '=', 6)])
            for ids in fleet_obj:
                vehicle_list.append(ids.id)
            res = {}
            # vehicle_list.append(self.vehicle_id.id)
            res['domain'] = {'new_vehicle_id': [('id', 'in', vehicle_list)]}
            msg1 = ("This is my debug message res')! %s", res)
            _logger.error(msg1)
            return res

    @api.onchange('total_other_charges_cost', 'total_damages_cost', 'additional_fine_ids', 'additional_toll_ids',
                  'additional_mileage_cost', 'additional_day_cost', 'additional_fuel_cost', 'total_other_charges_cost')
    def compute_invoicing_condition(self):
        if (self.total_other_charges_cost + self.total_damages_cost + self.additional_mileage_cost
                + self.additional_day_cost + self.additional_fuel_cost + self.total_other_charges_cost) > 0:
            self.can_be_invoiced = True
        else:
            self.can_be_invoiced = False

    rental_contract_id = fields.Many2one('account.analytic.account', string='Rental Contract')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    reason = fields.Char(string='Reason')
    can_be_invoiced = fields.Boolean(string="Can Be Invoiced?")
    state = fields.Char(string='State', help='Internal use to know the button use')
    fuel_level = fields.Selection([('0', 'Empty'),
                                   ('1', '1/8'),
                                   ('2', '2/8'),
                                   ('3', '3/8'),
                                   ('4', '4/8'),
                                   ('5', '5/8'),
                                   ('6', '6/8'),
                                   ('7', '7/8'),
                                   ('8', 'Full')],
                                  string='Fuel Level', readonly=False,
                                  related='vehicle_id.fuel_level')
    odometer = fields.Float(string='Odometer', related='vehicle_id.odometer', readonly=False)
    date = fields.Datetime('Handover Date', help="Date of Vehicle Handover", default=lambda s: datetime.now() + relativedelta(minute=0, second=0, hours=1))
    # dents
    hood_dent = fields.Boolean(string="Hood", default=True)
    # related = 'vehicle_id.hood_dent',
    front_r_door_dent = fields.Boolean(string="Front Door (R)", default=True)
    #related='vehicle_id.front_r_door_dent',
    front_l_door_dent = fields.Boolean(string="Front Door (L)", default=True)
    #, related='vehicle_id.front_l_door_dent'
    back_r_door_dent = fields.Boolean(string="Back Door (R)", default=True)
    #, related='vehicle_id.back_r_door_dent'
    back_l_door_dent = fields.Boolean(string="Back Door (L)", default=True)
    #related='vehicle_id.back_l_door_dent',
    boot_dent = fields.Boolean(string="Boot", default=True)
    #related='vehicle_id.boot_dent',

    # dent charges
    hood_dent_cost = fields.Float(string="Hood")
    #, related='vehicle_id.hood_dent_cost'
    front_r_door_dent_cost = fields.Float(string="Front Door (R)")
    # related='vehicle_id.front_r_door_dent_cost'
    front_l_door_dent_cost = fields.Float(string="Front Door (L)")
    # , related = 'vehicle_id.front_l_door_dent_cost'
    back_r_door_dent_cost = fields.Float(string="Back Door (R)")
    # , related = 'vehicle_id.back_r_door_dent_cost'
    back_l_door_dent_cost = fields.Float(string="Back Door (L)")
    # , related = 'vehicle_id.back_l_door_dent_cost'
    boot_dent_cost = fields.Float(string="Boot")
    # , related = 'vehicle_id.boot_dent_cost'
    # dent count
    hood_dent_count = fields.Integer(string="Hood", related='vehicle_id.hood_dent_count')
    front_r_door_dent_count = fields.Integer(string="  Front Door (R)", related='vehicle_id.front_r_door_dent_count')
    front_l_door_dent_count = fields.Integer(string="Front Door (L)", related='vehicle_id.front_l_door_dent_count')
    back_r_door_dent_count = fields.Integer(string="Back Door (R)", related='vehicle_id.back_r_door_dent_count')
    back_l_door_dent_count = fields.Integer(string="Back Door (L)", related='vehicle_id.back_l_door_dent_count')
    boot_dent_count = fields.Integer(string="Boot", related='vehicle_id.boot_dent_count')
    # new dent count
    hood_dent_count_new = fields.Integer(string="Hood")

    @api.constrains('hood_dent_count_new')
    def _check_positive_hood_dent_count_new(self):
        for record in self:
            if record.hood_dent_count_new < 0:
                raise ValidationError("Count must be a positive value.")

    front_r_door_dent_count_new = fields.Integer(string="Front Door (R)")

    @api.constrains('front_r_door_dent_count_new')
    def _check_positive_front_r_door_dent_count_new(self):
        for record in self:
            if record.front_r_door_dent_count_new < 0:
                raise ValidationError("Count must be a positive value.")
    front_l_door_dent_count_new = fields.Integer(string="Front Door (L)")

    @api.constrains('front_l_door_dent_count_new')
    def _check_positive_front_l_door_dent_count_new(self):
        for record in self:
            if record.front_l_door_dent_count_new < 0:
                raise ValidationError("Count must be a positive value.")
    back_r_door_dent_count_new = fields.Integer(string="Back Door (R)")

    @api.constrains('back_r_door_dent_count_new')
    def _check_positive_back_r_door_dent_count_new(self):
        for record in self:
            if record.back_r_door_dent_count_new < 0:
                raise ValidationError("Count must be a positive value.")
    back_l_door_dent_count_new = fields.Integer(string="Back Door (L)")

    @api.constrains('back_l_door_dent_count_new')
    def _check_positive_back_l_door_dent_count_new(self):
        for record in self:
            if record.back_l_door_dent_count_new < 0:
                raise ValidationError("Count must be a positive value.")
    boot_dent_count_new = fields.Integer(string="Boot")
    # scratches
    hood_scratch = fields.Boolean(string="Hood", related='vehicle_id.hood_scratch', default=True)
    front_r_door_scratch = fields.Boolean(string="Front Door (R)", related='vehicle_id.front_r_door_scratch',
                                          default=True)
    front_l_door_scratch = fields.Boolean(string="Front Door (L)", related='vehicle_id.front_l_door_scratch',
                                          default=True)
    back_r_door_scratch = fields.Boolean(string="Back Door (R)", related='vehicle_id.back_r_door_scratch', default=True)
    back_l_door_scratch = fields.Boolean(string="Back Door (L)", related='vehicle_id.back_l_door_scratch', default=True)
    boot_scratch = fields.Boolean(string="Boot", related='vehicle_id.boot_scratch', default=True)
    # scratch charges
    hood_scratch_cost = fields.Float(string="Hood")
    # , related = 'vehicle_id.hood_scratch_cost'
    front_r_door_scratch_cost = fields.Float(string="Front Door (R)")
    # , related = 'vehicle_id.front_r_door_scratch_cost'
    front_l_door_scratch_cost = fields.Float(string="Front Door (L)")
    # , related = 'vehicle_id.front_l_door_scratch_cost'
    back_r_door_scratch_cost = fields.Float(string="Back Door (R)")
    # , related = 'vehicle_id.back_r_door_scratch_cost'
    back_l_door_scratch_cost = fields.Float(string="Back Door (L)")
    # , related = 'vehicle_id.back_l_door_scratch_cost'
    boot_scratch_cost = fields.Float(string="Boot")
    # , related = 'vehicle_id.boot_scratch_cost'
    # scratch count
    hood_scratch_count = fields.Integer(string="Hood", related='vehicle_id.hood_scratch_count')
    front_r_door_scratch_count = fields.Integer(string="Front Door (R)",
                                                related='vehicle_id.front_r_door_scratch_count')
    front_l_door_scratch_count = fields.Integer(string="Front Door (L)",
                                                related='vehicle_id.front_l_door_scratch_count')
    back_r_door_scratch_count = fields.Integer(string="Back Door (R)", related='vehicle_id.back_r_door_scratch_count')
    back_l_door_scratch_count = fields.Integer(string="Back Door (L)", related='vehicle_id.back_l_door_scratch_count')
    boot_scratch_count = fields.Integer(string="Boot", related='vehicle_id.boot_scratch_count')
    # New Scratch Count
    hood_scratch_count_new = fields.Integer(string="Hood")
    front_r_door_scratch_count_new = fields.Integer(string="Front Door (R)")
    front_l_door_scratch_count_new = fields.Integer(string="Front Door (L)")
    back_r_door_scratch_count_new = fields.Integer(string="Back Door (R)")

    back_l_door_scratch_count_new = fields.Integer(string="Back Door (L)")
    boot_scratch_count_new = fields.Integer(string="Boot")
    # for salik and fines
    additional_toll_ids = fields.One2many('vehicle.salik.charge', 'contract_details',
                                          string='Toll Charge')
    additional_fine_ids = fields.One2many('vehicle.fine.charge', 'contract_details',
                                          string='Fine Charge')
    # additional charges
    total_damages_cost = fields.Float(string='Total Damages Amount', currency_field='currency_id')
    additional_mileage_cost = fields.Float(string='Additional Mileage Charge', currency_field='currency_id')
    total_other_charges_cost = fields.Float(string='Total Fine and Salik Charges', currency_field='currency_id')
    additional_day_cost = fields.Float(string='Additional Day Charge', currency_field='currency_id')
    additional_fuel_cost = fields.Float(string='Additional Fuel Cost', currency_field='currency_id')
    vehicle_returned_for_replacement = fields.Boolean(string='Vehicle Returned for replacement', default=False)
    new_vehicle_id = fields.Many2one('fleet.vehicle', string='Replacement Vehicle')

    def get_dent_scratch_products(self):
        total_dent_cost = self.hood_dent_cost + self.front_r_door_dent_cost + self.front_l_door_dent_cost + \
                          self.back_r_door_dent_cost + self.back_l_door_dent_cost + self.boot_dent_cost
        total_scratch_cost = self.hood_scratch_cost + self.front_r_door_scratch_cost + self.boot_scratch_cost + \
                             self.front_l_door_scratch_cost + self.back_r_door_scratch_cost + self.back_l_door_scratch_cost
        additional_product_obj = self.env['rental.wizard.extra.charges']
        if total_dent_cost > 0:
            new_product = self.env.ref('fleet_rent.additional_charge_dents').product_variant_id
            new_additional_product = {'additional_charge_product_id': new_product.id,
                                      'unit_measure': new_product.uom_id.id,
                                      'unit_price': total_dent_cost,
                                      'description': 'Plate No: ' + self.vehicle_id.license_plate +
                                                     ' | Total Cost of Dents ' +
                                                     self.vehicle_id.license_plate if self.state == 'replacement' else '',
                                      'product_uom_qty': 1,
                                      'cost': total_dent_cost,
                                      'agreement_id': self.rental_contract_id.id}
            new_product = additional_product_obj.create(new_additional_product)
            # if self.rental_contract_id.rental_terms == 'spot':
            self.create_move_lines(new_product)
        if total_scratch_cost > 0:
            new_product = self.env.ref('fleet_rent.additional_charge_scratches').product_variant_id
            new_additional_product = {'additional_charge_product_id': new_product.id,
                                      'unit_measure': new_product.uom_id.id,
                                      'unit_price': total_scratch_cost,
                                      'description': 'Plate No: ' + self.vehicle_id.license_plate +
                                                     ' | Total Cost of Scratches ' +
                                                     self.vehicle_id.license_plate if self.state == 'replacement' else '',
                                      'product_uom_qty': 1,
                                      'cost': total_scratch_cost,
                                      'agreement_id': self.rental_contract_id.id}
            new_product = additional_product_obj.create(new_additional_product)
            self.create_move_lines(new_product)
            # if self.rental_contract_id.rental_terms == 'spot':
            # self.create_move_lines(new_product)

    def get_toll_fine_amount(self):
        additional_product_obj = self.env['rental.wizard.extra.charges']
        vehicle_salik_and_fines = self.env['vehicle.rental.fines']
        salik = fine = 0

        if self.additional_fine_ids:
            for each in self.additional_fine_ids:
                new_additional_product = {'additional_charge_product_id': each.fine_product_id.id,
                                          'unit_measure': each.fine_product_id.uom_id.id,
                                          'unit_price': each.unit_price,
                                          'product_uom_qty': 1,
                                          'description': 'Plate No: ' + self.vehicle_id.license_plate + ' | Date: ' +
                                                         str(each.time_date) + ' | Fine Loc.: ' + each.location +
                                                         ' | Description: ' + (each.description or ''),
                                          'cost': each.unit_price,
                                          'agreement_id': self.rental_contract_id.id}
                new_product = additional_product_obj.create(new_additional_product)
                a = vehicle_salik_and_fines.create({'vehicle_id': self.vehicle_id.id,
                                                'description': each.description,
                                                'time_date': each.time_date,
                                                'location': each.location,
                                                'amount': each.unit_price,
                                                'analytic_account_id': self.rental_contract_id.id,
                                                'fine_or_toll': '0'})
                # if self.rental_contract_id.rental_terms == 'spot':
                self.create_move_lines(new_product)
                salik += each.unit_price
        if self.additional_toll_ids:
            for each in self.additional_toll_ids:
                new_additional_product = {'additional_charge_product_id': each.salik_product_id.id,
                                          'unit_measure': each.salik_product_id.uom_id.id,
                                          'unit_price': each.unit_price,
                                          'product_uom_qty': 1,
                                          'description': 'Plate No: ' + self.vehicle_id.license_plate + ' | Date: ' +
                                                         str(each.time_date) + ' | Toll Loc.: ' + each.location +
                                                         ' | Description: ' + (each.description or ''),
                                          'cost': each.unit_price,
                                          'agreement_id': self.rental_contract_id.id}
                new_product = additional_product_obj.create(new_additional_product)
                # if self.rental_contract_id.rental_terms == 'spot':
                self.create_move_lines(new_product)
                b = vehicle_salik_and_fines.create({'vehicle_id': self.vehicle_id.id,
                                                'description': each.description,
                                                'time_date': each.time_date,
                                                'location': each.location,
                                                'amount': each.unit_price,
                                                'analytic_account_id': self.rental_contract_id.id,
                                                'fine_or_toll': '1'})
                fine += each.unit_price
        return salik + fine

    def create_move_lines(self, additional_product):
        tenancy_rent_schedule_obj = self.env['tenancy.rent.schedule']
        tenancy_rent_schedule_items = tenancy_rent_schedule_obj.search([('tenancy_id', '=', self.rental_contract_id.id)])
        invc_draft_status = False
        inv_line_main = {
            # 'origin': 'tenancy.rent.schedule',
            'name': additional_product.additional_charge_product_id.name,
            'price_unit': additional_product.unit_price or 0.00,
            'price_subtotal': additional_product.cost or 0.00,
            'quantity': additional_product.product_uom_qty,
            'product_uom_id': additional_product.unit_measure,
            'account_id': self.vehicle_id.income_acc_id.id or False,
            'analytic_account_id': self.vehicle_id.analytic_account_id.id or False,
            'tax_ids': additional_product.additional_charge_product_id.taxes_id,
            'description': additional_product.description,
            'vehicle_id': self.vehicle_id.id,
        }


        # code for adding invoice lines,
        # if the invoice not confirmed at the time of rental contract return state or close state
        if tenancy_rent_schedule_items:
            for each in tenancy_rent_schedule_items:
                if each.invc_id.state == 'draft':
                    invc_draft_status = True
                    each.invc_id.update({'invoice_line_ids': [(0, 0, inv_line_main)]})
                    each.tenancy_id.account_move_line_ids = each.invc_id.line_ids
                    each.amount = each.invc_id.amount_total
                    if self.rental_contract_id.state == 'open' and len(tenancy_rent_schedule_items.ids) == 1:
                        desc = each.invc_id.invoice_line_ids[0].description.split('Return Odo.:')[0]
                        each.invc_id.invoice_line_ids[0].write({'description': desc + 'Return Odo.: ' +
                                                               str(self.odometer) + ' | Return Fuel Lvl: ' +
                                                               str(self.fuel_level)})
                    return True

        # code for creating invoices for rental contract,
        # if the invoice confirmed before rental contract return state or close
        if not invc_draft_status:
            journal_ids = self.env['account.journal'].search([('type', '=', 'sale')])
            d1 = datetime.strptime(str(self.rental_contract_id.date_start), DT)
            if self.rental_contract_id.invoice_policies == 'advanced':
                d1 = d1 + relativedelta(months=int(1))
                rent_schedule = tenancy_rent_schedule_obj.create({
                    'start_date': d1.strftime(DT),
                    'amount': self.rental_contract_id.rent + self.rental_contract_id.additional_charges,
                    'vehicle_id': self.vehicle_id and self.vehicle_id.id or False,
                    'tenancy_id': self.rental_contract_id.id,
                    'single_inv': True,
                    'currency_id': self.rental_contract_id.currency_id.id or False,
                    'rel_tenant_id': self.rental_contract_id.tenant_id.id or False
                })
                if rent_schedule.tenancy_id.multi_prop:
                    for data in rent_schedule.tenancy_id.prop_id:
                        for account in data.property_ids.income_acc_id:
                            inv_line_main.update({'account_id': account.id})
                inv_values = {
                    'partner_id': rent_schedule.tenancy_id and rent_schedule.tenancy_id.tenant_id and rent_schedule.tenancy_id.tenant_id.id or False,
                    'move_type': 'out_invoice',
                    'fleet_vehicle_id': self.vehicle_id.id or False,
                    'date_invoice': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) or False,
                    'invoice_date': rent_schedule.start_date or False,
                    'journal_id': journal_ids and journal_ids[0].id or False,
                    'state': 'draft',
                    'invoice_line_ids': [(0, 0, inv_line_main)]
                }
                acc_id = self.env['account.move'].create(inv_values)
                rent_schedule.write({'invc_id': acc_id.id, 'inv': True, 'amount': acc_id.amount_total})
                rent_schedule.tenancy_id.account_move_line_ids = acc_id.line_ids
                context = dict(self._context or {})
                wiz_form_id = self.env.ref('account.view_move_form').id
                return {
                    'view_type': 'form',
                    'view_id': wiz_form_id,
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'res_id': rent_schedule.invc_id.id,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'context': context,
                }

    def confirm_handover(self):
        if self.rental_contract_id:
            self.rental_contract_id.replace_vehicle_details.create({'re_vehicle': self.vehicle_id.id,
                                                                    'replace_id': self.rental_contract_id.id,
                                                                    'start_date': self.date,
                                                                    'current_odometer': self.odometer})
        if self.fuel_level:
            self.rental_contract_id.fuel_level_temp = self.fuel_level

        if self._context.get('active_id', False) and self._context.get('active_model', False):
            for reason in self.env[self._context['active_model']].browse(self._context.get('active_id', False)):
                reason.write({'state': 'open',
                              'current_odometer': self.odometer,
                              'date_start': self.date})

                value = fields.Datetime.context_timestamp(self, reason.date_start).strftime(DT)

                for each in reason.extra_charges_ids:
                    desc = each.description.split('| Start Date:')[0] + '| Start Date: ' \
                           + str(value) + '| Start Odo.: ' \
                           + each.description.split('| Start Odo.: ')[1]
                    each.write({'description': desc})
                    break
                # raise UserError(_('Please add some items to move.'))
        if self.vehicle_id:
            self.vehicle_id.update({'hood_dent': self.hood_dent,
                                    'front_r_door_dent': self.front_r_door_dent,
                                    'front_l_door_dent': self.front_l_door_dent,
                                    'back_r_door_dent': self.back_r_door_dent,
                                    'back_l_door_dent': self.back_l_door_dent,
                                    'boot_dent': self.boot_dent,
                                    'hood_scratch': self.hood_scratch,
                                    'front_r_door_scratch': self.front_r_door_scratch,
                                    'front_l_door_scratch': self.front_l_door_scratch,
                                    'back_r_door_scratch': self.back_r_door_scratch,
                                    'back_l_door_scratch': self.back_l_door_scratch,
                                    'boot_scratch': self.boot_scratch,
                                    'hood_dent_count': self.hood_dent_count + self.hood_dent_count_new,
                                    'front_r_door_dent_count': self.front_r_door_dent_count + self.front_r_door_dent_count_new,
                                    'front_l_door_dent_count': self.front_l_door_dent_count + self.front_l_door_dent_count_new,
                                    'back_r_door_dent_count': self.back_r_door_dent_count + self.back_r_door_dent_count_new,
                                    'back_l_door_dent_count': self.back_l_door_dent_count + self.back_l_door_dent_count_new,
                                    'boot_dent_count': self.boot_dent_count + self.boot_dent_count_new,
                                    'hood_scratch_count': self.hood_scratch_count + self.hood_scratch_count_new,
                                    'front_r_door_scratch_count': self.front_r_door_scratch_count + self.front_r_door_scratch_count_new,
                                    'front_l_door_scratch_count': self.front_l_door_scratch_count + self.front_l_door_scratch_count_new,
                                    'back_r_door_scratch_count': self.back_r_door_scratch_count + self.back_r_door_scratch_count_new,
                                    'back_l_door_scratch_count': self.back_l_door_scratch_count + self.back_l_door_scratch_count_new,
                                    'boot_scratch_count': self.boot_scratch_count + self.boot_scratch_count_new,
                                    'state': 'rent',
                                    'state_id': 9,
                                    'odometer': self.odometer,
                                    'active_contract': self.rental_contract_id})
        return True

    def get_bulk_toll_fine_amount(self):
        # rental_table = self.env['fleet.rental.vehicle.details'].search(
        #     [('rental_contract_id', '=', self.id), ('vehicle_id', '=', self.vehicle_id.id),
        #      ('state', '=', 'hand_over')])
        bulk_toll_fine_charge = self.env['vehicle.rental.fines']
        salik_table = self.env['vehicle.salik.charge']
        fine_table = self.env['vehicle.fine.charge']
        main_val = bulk_toll_fine_charge.search([('analytic_account_id', '=', self.rental_contract_id.id)])
        toll_id = self.env.ref('fleet_rent.additional_charge_toll_charges').product_variant_id
        fine_id = self.env.ref('fleet_rent.additional_charge_fines').product_variant_id
        for each in main_val:
            if each.fine_or_toll == '1':
                salik_table.create({'salik_product_id': toll_id.id,
                                    'analytic_account_id': each.analytic_account_id.id,
                                    'vehicle_id': each.vehicle_id.id,
                                    'unit_price': each.amount,
                                    'location': each.location,
                                    'description': each.description,
                                    'contract_details': self.id,
                                    })
            if each.fine_or_toll == '0':
                fine_table.create({'fine_product_id': fine_id.id,
                                   'analytic_account_id': each.analytic_account_id.id,
                                   'vehicle_id': each.vehicle_id.id,
                                   'unit_price': each.amount,
                                   'location': each.location,
                                   'description': each.description,
                                   'contract_details': self.id,
                                   })

    def confirm_return(self):

        self.get_bulk_toll_fine_amount()
        self.compute_total_extra_day_usage()
        self.compute_total_extra_mileage_usage()
        self.computing_extra_fuel_cost()
        total_other_charges_cost = 0
        if self.additional_fine_ids or self.additional_toll_ids:
            self.total_other_charges_cost = self.get_toll_fine_amount()
        # calling dents and scratches
        if self.total_damages_cost:
            self.get_dent_scratch_products()
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        tenancy_id.write({'reason': self.reason,
                          'date': self.date,
                          'odometer': self.odometer,
                          'fuel_level': self.fuel_level,
                          'hood_dent': self.hood_dent,
                          'front_r_door_dent': self.front_r_door_dent,
                          'front_l_door_dent': self.front_l_door_dent,
                          'back_r_door_dent': self.back_r_door_dent,
                          'back_l_door_dent': self.back_l_door_dent,
                          'boot_dent': self.boot_dent,
                          'hood_scratch': self.hood_scratch,
                          'front_r_door_scratch': self.front_r_door_scratch,
                          'front_l_door_scratch': self.front_l_door_scratch,
                          'back_r_door_scratch': self.back_r_door_scratch,
                          'back_l_door_scratch': self.back_l_door_scratch,
                          'boot_scratch': self.boot_scratch,
                          'hood_dent_count': self.hood_dent_count + self.hood_dent_count_new,
                          'front_r_door_dent_count': self.front_r_door_dent_count + self.front_r_door_dent_count_new,
                          'front_l_door_dent_count': self.front_l_door_dent_count + self.front_l_door_dent_count_new,
                          'back_r_door_dent_count': self.back_r_door_dent_count + self.back_r_door_dent_count_new,
                          'back_l_door_dent_count': self.back_l_door_dent_count + self.back_l_door_dent_count_new,
                          'boot_dent_count': self.boot_dent_count + self.boot_dent_count_new,
                          'hood_scratch_count': self.hood_scratch_count + self.hood_scratch_count_new,
                          'front_r_door_scratch_count': self.front_r_door_scratch_count + self.front_r_door_scratch_count_new,
                          'front_l_door_scratch_count': self.front_l_door_scratch_count + self.front_l_door_scratch_count_new,
                          'back_r_door_scratch_count': self.back_r_door_scratch_count + self.back_r_door_scratch_count_new,
                          'back_l_door_scratch_count': self.back_l_door_scratch_count + self.back_l_door_scratch_count_new,
                          'boot_scratch_count': self.boot_scratch_count + self.boot_scratch_count_new,
                          'state': 'return',
                          'additional_fine_ids': self.additional_fine_ids,
                          'additional_toll_ids': self.additional_toll_ids,
                          'total_damages_cost': self.hood_dent_cost + self.front_r_door_dent_cost + self.front_l_door_dent_cost + \
                self.back_r_door_dent_cost + self.back_l_door_dent_cost + self.boot_dent_cost +
self.hood_scratch_cost + self.front_r_door_scratch_cost + self.boot_scratch_cost + \
                                 self.front_l_door_scratch_cost + self.back_r_door_scratch_cost + self.back_l_door_scratch_cost
                          })
        if tenancy_id.rental_contract_id:
            for reason in tenancy_id.rental_contract_id:
                reason.write({'state': 'return',
                              'duration_cover': self.reason,
                              'closing_odometer': self.odometer,
                              'closing_odometer_temp': reason.vehicle_id_temp.odometer,
                              'date': self.date,
                              'total_other_charges_cost': self.total_other_charges_cost,
                              'cancel_by_id': self._uid})
                desc = reason.extra_charges_ids[0].description.split('Return Odo.:')[0]
                reason.extra_charges_ids[0].write({'description': desc
                                                                  + ' Return Date: ' + str(self.date)
                                                                  + ' Return Odo.: ' + str(self.odometer)
                                                                  + ' | Return Fuel Lvl: ' + str(self.fuel_level)})
                contract_id = self.env['account.analytic.account'].search([('id', '=', self.rental_contract_id.id)])
                ten_id = self.env['tenancy.rent.schedule'].search([('tenancy_id', '=', contract_id.id)])
                ten_id.invc_id[0].invoice_line_ids[0].update({
                    'description': reason.extra_charges_ids[0].description
                })

        if self.vehicle_id:
            self.vehicle_id.update({'hood_dent': self.hood_dent,
                                    'active_contract': False,
                                    'front_r_door_dent': self.front_r_door_dent,
                                    'front_l_door_dent': self.front_l_door_dent,
                                    'back_r_door_dent': self.back_r_door_dent,
                                    'back_l_door_dent': self.back_l_door_dent,
                                    'boot_dent': self.boot_dent,
                                    'hood_scratch': self.hood_scratch,
                                    'front_r_door_scratch': self.front_r_door_scratch,
                                    'front_l_door_scratch': self.front_l_door_scratch,
                                    'back_r_door_scratch': self.back_r_door_scratch,
                                    'back_l_door_scratch': self.back_l_door_scratch,
                                    'boot_scratch': self.boot_scratch,
                                    'hood_dent_count': self.hood_dent_count + self.hood_dent_count_new,
                                    'front_r_door_dent_count': self.front_r_door_dent_count + self.front_r_door_dent_count_new,
                                    'front_l_door_dent_count': self.front_l_door_dent_count + self.front_l_door_dent_count_new,
                                    'back_r_door_dent_count': self.back_r_door_dent_count + self.back_r_door_dent_count_new,
                                    'back_l_door_dent_count': self.back_l_door_dent_count + self.back_l_door_dent_count_new,
                                    'boot_dent_count': self.boot_dent_count + self.boot_dent_count_new,
                                    'hood_scratch_count': self.hood_scratch_count + self.hood_scratch_count_new,
                                    'front_r_door_scratch_count': self.front_r_door_scratch_count + self.front_r_door_scratch_count_new,
                                    'front_l_door_scratch_count': self.front_l_door_scratch_count + self.front_l_door_scratch_count_new,
                                    'back_r_door_scratch_count': self.back_r_door_scratch_count + self.back_r_door_scratch_count_new,
                                    'back_l_door_scratch_count': self.back_l_door_scratch_count + self.back_l_door_scratch_count_new,
                                    'boot_scratch_count': self.boot_scratch_count + self.boot_scratch_count_new,
                                    'state': 'inspection',
                                    'state_id': 5,
                                    'odometer': self.odometer,
                                    'fuel_level': self.fuel_level})

            v_log_obj = self.rental_contract_id.replace_vehicle_details
            for i in range(len(v_log_obj)):
                if self.rental_contract_id.replace_vehicle_details[i].end_date == False:
                    self.rental_contract_id.replace_vehicle_details[i].update({
                        'end_date': self.date})
                if self.rental_contract_id.replace_vehicle_details[i].closing_odometer == False:
                    self.rental_contract_id.replace_vehicle_details[i].update({
                        'closing_odometer': self.rental_contract_id.closing_odometer})
        return True

    # @api.multi
    def confirm_rent_close(self):
        total_other_charges_cost = 0
        if self.additional_fine_ids or self.additional_toll_ids:
            total_other_charges_cost = self.get_toll_fine_amount()
            # self.create_invoice_and_close_rent()
        if self._context.get('active_id', False) and self._context.get('active_model', False):
            for reason in self.env[self._context['active_model']].browse(self._context.get('active_id', False)):
                reason.rental_contract_id.write({'state': 'close',
                                                 'date_cancel': date.today(),
                                                 'cancel_by_id': self._uid,
                                                 'total_other_charges_cost': total_other_charges_cost})
                self.vehicle_id.update({'state_id': 6})
        return True

    def confirm_replacement_return(self):
        if self.additional_fine_ids or self.additional_toll_ids:
            total_other_charges_cost = self.get_toll_fine_amount()
        if self.total_damages_cost:
            self.get_dent_scratch_products()
        total_count = self.env['fleet.rental.vehicle.details'].search_count([
                ('rental_contract_id', '=', self.rental_contract_id.id)])
        if total_count > 2:
            fleet_vehicle_state = self.env['fleet.vehicle.state'].search([('name', '=', 'Available')]).id
        else:
            fleet_vehicle_state = self.env['fleet.vehicle.state'].search([('name', '=', 'In shop')]).id

        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))

        tenancy_id.write({'reason': self.reason,
                          'date': self.date,
                          'odometer': self.odometer,
                          'fuel_level': self.fuel_level,
                          'hood_dent': self.hood_dent,
                          'front_r_door_dent': self.front_r_door_dent,
                          'front_l_door_dent': self.front_l_door_dent,
                          'back_r_door_dent': self.back_r_door_dent,
                          'back_l_door_dent': self.back_l_door_dent,
                          'boot_dent': self.boot_dent,
                          'hood_scratch': self.hood_scratch,
                          'front_r_door_scratch': self.front_r_door_scratch,
                          'front_l_door_scratch': self.front_l_door_scratch,
                          'back_r_door_scratch': self.back_r_door_scratch,
                          'back_l_door_scratch': self.back_l_door_scratch,
                          'boot_scratch': self.boot_scratch,
                          'hood_dent_count': self.hood_dent_count + self.hood_dent_count_new,
                          'front_r_door_dent_count': self.front_r_door_dent_count + self.front_r_door_dent_count_new,
                          'front_l_door_dent_count': self.front_l_door_dent_count + self.front_l_door_dent_count_new,
                          'back_r_door_dent_count': self.back_r_door_dent_count + self.back_r_door_dent_count_new,
                          'back_l_door_dent_count': self.back_l_door_dent_count + self.back_l_door_dent_count_new,
                          'boot_dent_count': self.boot_dent_count + self.boot_dent_count_new,
                          'hood_scratch_count': self.hood_scratch_count + self.hood_scratch_count_new,
                          'front_r_door_scratch_count': self.front_r_door_scratch_count + self.front_r_door_scratch_count_new,
                          'front_l_door_scratch_count': self.front_l_door_scratch_count + self.front_l_door_scratch_count_new,
                          'back_r_door_scratch_count': self.back_r_door_scratch_count + self.back_r_door_scratch_count_new,
                          'back_l_door_scratch_count': self.back_l_door_scratch_count + self.back_l_door_scratch_count_new,
                          'boot_scratch_count': self.boot_scratch_count + self.boot_scratch_count_new,
                          'state': 'replacement_return',
                          'additional_fine_ids': self.additional_fine_ids,
                          'additional_toll_ids': self.additional_toll_ids,
                          'total_damages_cost': self.hood_dent_cost + self.front_r_door_dent_cost + self.front_l_door_dent_cost + \
                                                self.back_r_door_dent_cost + self.back_l_door_dent_cost + self.boot_dent_cost +
                                                self.hood_scratch_cost + self.front_r_door_scratch_cost + self.boot_scratch_cost + \
                                                self.front_l_door_scratch_cost + self.back_r_door_scratch_cost + self.back_l_door_scratch_cost
                          })

        if self.vehicle_id:
            self.vehicle_id.update({'hood_dent': self.hood_dent,
                                    'active_contract': False,
                                    'front_r_door_dent': self.front_r_door_dent,
                                    'front_l_door_dent': self.front_l_door_dent,
                                    'back_r_door_dent': self.back_r_door_dent,
                                    'back_l_door_dent': self.back_l_door_dent,
                                    'boot_dent': self.boot_dent,
                                    'hood_scratch': self.hood_scratch,
                                    'front_r_door_scratch': self.front_r_door_scratch,
                                    'front_l_door_scratch': self.front_l_door_scratch,
                                    'back_r_door_scratch': self.back_r_door_scratch,
                                    'back_l_door_scratch': self.back_l_door_scratch,
                                    'boot_scratch': self.boot_scratch,
                                    'hood_dent_count': self.hood_dent_count + self.hood_dent_count_new,
                                    'front_r_door_dent_count': self.front_r_door_dent_count + self.front_r_door_dent_count_new,
                                    'front_l_door_dent_count': self.front_l_door_dent_count + self.front_l_door_dent_count_new,
                                    'back_r_door_dent_count': self.back_r_door_dent_count + self.back_r_door_dent_count_new,
                                    'back_l_door_dent_count': self.back_l_door_dent_count + self.back_l_door_dent_count_new,
                                    'boot_dent_count': self.boot_dent_count + self.boot_dent_count_new,
                                    'hood_scratch_count': self.hood_scratch_count + self.hood_scratch_count_new,
                                    'front_r_door_scratch_count': self.front_r_door_scratch_count + self.front_r_door_scratch_count_new,
                                    'front_l_door_scratch_count': self.front_l_door_scratch_count + self.front_l_door_scratch_count_new,
                                    'back_r_door_scratch_count': self.back_r_door_scratch_count + self.back_r_door_scratch_count_new,
                                    'back_l_door_scratch_count': self.back_l_door_scratch_count + self.back_l_door_scratch_count_new,
                                    'boot_scratch_count': self.boot_scratch_count + self.boot_scratch_count_new,
                                    'state': 'replacement',
                                    'state_id': fleet_vehicle_state,
                                    'odometer': self.odometer,
                                    'fuel_level': self.fuel_level})
        replacement_vehicle_new = self.env['fleet.rental.vehicle.details'].create({
            'rental_contract_id': self.rental_contract_id.id,
            'state': 'replacement_handover',
            'vehicle_id': self.new_vehicle_id.id})

        v_log_obj = self.rental_contract_id.replace_vehicle_details
        v_log_obj.update({
            'closing_odometer': self.vehicle_id.odometer,
            'end_date': self.date})
        wiz_form_id = self.env.ref(
            'fleet_analytic_accounting.fleet_rental_contract_replacement_vehicle_handover_details_wizard').id

        return {
            'name': 'Replacement Handover',
            'res_model': 'fleet.rental.vehicle.details',
            'type': 'ir.actions.act_window',
            'view_id': wiz_form_id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
            'res_id': replacement_vehicle_new.id
        }

    def confirm_replacement_handover(self):

        if self.rental_contract_id:
            self.rental_contract_id.write({'vehicle_id': self.vehicle_id.id,
                                           'current_odometer': self.odometer})
            self.rental_contract_id.write({'current_odometer': self.odometer})
        rent_id = self.env['replace.vehicle.log'].search([('replace_id', '=', self.rental_contract_id.id)])
        # if rent_id:
        #     rent_id.update({'end_date': datetime.now()})
        if self.rental_contract_id:
            self.rental_contract_id.replace_vehicle_details.create({'re_vehicle': self.vehicle_id.id,
                                                                    'replace_id': self.rental_contract_id.id,
                                                                    'start_date': self.date,
                                                                    'current_odometer': self.odometer})

        if self.vehicle_id:
            fleet_vehicle_state = self.env['fleet.vehicle.state'].search([('name', '=', 'Replaced')])
            self.vehicle_id.update({'hood_dent': self.hood_dent,
                                    'front_r_door_dent': self.front_r_door_dent,
                                    'front_l_door_dent': self.front_l_door_dent,
                                    'back_r_door_dent': self.back_r_door_dent,
                                    'back_l_door_dent': self.back_l_door_dent,
                                    'boot_dent': self.boot_dent,
                                    'hood_scratch': self.hood_scratch,
                                    'front_r_door_scratch': self.front_r_door_scratch,
                                    'front_l_door_scratch': self.front_l_door_scratch,
                                    'back_r_door_scratch': self.back_r_door_scratch,
                                    'back_l_door_scratch': self.back_l_door_scratch,
                                    'boot_scratch': self.boot_scratch,
                                    'hood_dent_count': self.hood_dent_count + self.hood_dent_count_new,
                                    'front_r_door_dent_count': self.front_r_door_dent_count + self.front_r_door_dent_count_new,
                                    'front_l_door_dent_count': self.front_l_door_dent_count + self.front_l_door_dent_count_new,
                                    'back_r_door_dent_count': self.back_r_door_dent_count + self.back_r_door_dent_count_new,
                                    'back_l_door_dent_count': self.back_l_door_dent_count + self.back_l_door_dent_count_new,
                                    'boot_dent_count': self.boot_dent_count + self.boot_dent_count_new,
                                    'hood_scratch_count': self.hood_scratch_count + self.hood_scratch_count_new,
                                    'front_r_door_scratch_count': self.front_r_door_scratch_count + self.front_r_door_scratch_count_new,
                                    'front_l_door_scratch_count': self.front_l_door_scratch_count + self.front_l_door_scratch_count_new,
                                    'back_r_door_scratch_count': self.back_r_door_scratch_count + self.back_r_door_scratch_count_new,
                                    'back_l_door_scratch_count': self.back_l_door_scratch_count + self.back_l_door_scratch_count_new,
                                    'boot_scratch_count': self.boot_scratch_count + self.boot_scratch_count_new,
                                    'state': 'rent',
                                    'state_id': fleet_vehicle_state.id,
                                    'odometer': self.odometer,
                                    'active_contract': self.rental_contract_id})
        return True
