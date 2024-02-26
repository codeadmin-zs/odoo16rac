from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DT
from dateutil.relativedelta import relativedelta


class WizardRentReturnReason(models.TransientModel):
    _name = 'rent.return.reason'

    @api.onchange('hood_dent_cost', 'front_r_door_dent_cost', 'front_l_door_dent_cost', 'back_r_door_dent_cost',
                  'back_l_door_dent_cost',
                  'boot_dent_cost', 'hood_scratch_cost', 'hood_scratch_cost', 'front_r_door_scratch_cost',
                  'front_l_door_scratch_cost',
                  'back_r_door_scratch_cost', 'back_l_door_scratch_cost', 'boot_scratch_cost')
    def compute_total_damages_cost(self):
        total_damages_cost = self.hood_dent_cost + self.front_r_door_dent_cost + self.front_l_door_dent_cost + self.back_r_door_dent_cost + \
                             self.back_l_door_dent_cost + self.boot_dent_cost + self.hood_scratch_cost + self.front_r_door_scratch_cost + \
                             self.front_l_door_scratch_cost + self.back_r_door_scratch_cost + self.back_l_door_scratch_cost + self.boot_scratch_cost
        self.total_damages_cost = total_damages_cost
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        tenancy_id.total_damages_cost = total_damages_cost

    @api.onchange('fuel_level')
    def computing_extra_fuel_cost(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        current_fuel_level = int(self.fuel_level)
        fuel_level_at_handover = int(tenancy_id.vehicle_id.fuel_level)
        additional_fuel_cost = 0
        acc = []
        if current_fuel_level < fuel_level_at_handover:
            additional_product_obj = self.env['rental.wizard.fleet.additional.charges']
            fuel = tenancy_id.vehicle_id.model_id.category_vehicle_fuel_id.id
            new_product_template = self.env['product.template'].search([('accessories_ok', '=', True),
                                                                        ('name', '=', 'Fuel: ' + fuel.name)]).id
            new_product = self.env['product.product'].search([('product_tmpl_id', '=', new_product_template)])
            # new_product = self.env.ref('fleet_rent.additional_charge_extra_days').product_variant_id
            fuel_rate = new_product.lst_price
            fuel_tank_capacity = tenancy_id.vehicle_id.model_id.fuel_tank_capacity/8
            extra_fuels_used = (fuel_level_at_handover - current_fuel_level) * fuel_tank_capacity
            additional_fuel_cost = fuel_rate * extra_fuels_used
            new_additional_product = {'additional_charge_product_id': new_product.id,
                                      'unit_measure': new_product.uom_id.id,
                                      'unit_price': new_product.lst_price,
                                      'description': 'Additional Fuels Used - ' + str(extra_fuels_used),
                                      'product_uom_qty': extra_fuels_used,
                                      'cost': additional_fuel_cost,
                                      'agreement_id': tenancy_id.id}
            exist = False
            for each in tenancy_id.additional_rental_charges_ids:
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
                additional_product_obj.create(new_additional_product)
        self.additional_fuel_cost = additional_fuel_cost
        tenancy_id.additional_fuel_cost = additional_fuel_cost

    @api.onchange('return_date')
    def compute_total_extra_day_usage(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        start_date = tenancy_id.date_start.date()
        expected_return_date = tenancy_id.date.date()
        returned_date = self.return_date.date()
        additional_day_cost = 0.0
        additional_product_obj = self.env['rental.wizard.fleet.additional.charges']
        if expected_return_date < returned_date:
            # new_product = self.env['product.product'].search([('name', '=', 'Extra Days')])
            new_product = self.env.ref('fleet_rent.additional_charge_extra_days').product_variant_id
            extra_days = relativedelta(returned_date, expected_return_date).days
            extra_day_charge = tenancy_id.vehicle_id.vehicle_prodcut_template_id.extra_daily
            additional_day_cost = extra_days * extra_day_charge
            new_additional_product = {'additional_charge_product_id': new_product.id,
                                      'unit_measure': new_product.uom_id.id,
                                      'unit_price': new_product.lst_price,
                                      'description': 'Extra Days - ' + str(extra_days),
                                      'product_uom_qty': extra_days,
                                      'cost': additional_day_cost,
                                      'agreement_id': tenancy_id.id}
            exist = False
            for each in tenancy_id.additional_rental_charges_ids:
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
                additional_product_obj.create(new_additional_product)
        self.additional_day_cost = additional_day_cost
        tenancy_id.additional_day_cost = additional_day_cost

    @api.onchange('closing_odometer')
    def compute_total_extra_mileage_usage(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        tenancy_starting_odometer = tenancy_id.current_odometer
        allowed_mileage_per_day = tenancy_id.vehicle_id.vehicle_prodcut_template_id.allowd_daily_mileage
        tenancy_start_date = datetime.strptime(str(tenancy_id.date_start), '%Y-%m-%d %H:%M:%S')
        tenancy_expiry_date = datetime.strptime(str(tenancy_id.date), '%Y-%m-%d %H:%M:%S')
        contract_duration_in_days = (tenancy_expiry_date - tenancy_start_date).days
        total_allowed_mileage_for_contract = contract_duration_in_days * allowed_mileage_per_day
        additional_mileage_in_km = 0
        additional_mileage_cost = 0
        total_mileages = self.closing_odometer - tenancy_starting_odometer
        additional_product_obj = self.env['rental.wizard.fleet.additional.charges']
        if total_mileages > total_allowed_mileage_for_contract:
            additional_mileage_in_km = total_mileages - total_allowed_mileage_for_contract
            new_product = self.env.ref('fleet_rent.additional_charge_extra_kms').product_variant_id
            additional_mileage_cost = additional_mileage_in_km * new_product.lst_price
            new_additional_product = {'additional_charge_product_id': new_product.id,
                                      'unit_measure': new_product.uom_id.id,
                                      'unit_price': new_product.lst_price,
                                      'description': 'Additional KMs Used - ' + str(additional_mileage_in_km),
                                      'product_uom_qty': additional_mileage_in_km,
                                      'cost': additional_mileage_cost,
                                      'agreement_id': tenancy_id.id}
            exist = False
            for each in tenancy_id.additional_rental_charges_ids:
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
                additional_product_obj.create(new_additional_product)
        self.additional_mileage_cost = additional_mileage_cost
        tenancy_id.additional_mileage_cost = additional_mileage_cost

    @api.onchange('total_other_charges_cost', 'total_damages_cost',
                  'additional_mileage_cost', 'additional_day_cost', 'additional_fuel_cost')
    def compute_invoicing_condition(self):
        if (self.total_other_charges_cost + self.total_damages_cost
                + self.additional_mileage_cost + self.additional_day_cost + self.additional_fuel_cost) > 0:
            self.can_be_invoiced = True
            # rec.update({'can_be_invoiced': True })
        else:
            self.can_be_invoiced = False
            # rec.update({'can_be_invoiced': False })

    @api.depends('additional_charges_ids.cost')
    def _compute_additional_charges(self):
        for rec in self:
            charge_total = 0.0
            for line in rec.additional_charges_ids:
                charge_total += line.cost
            rec.update({'additional_charges': charge_total})

    def _default_vehicle_id_closing(self):
        if self.env.context.get('default_vehicle_id', False):
            return self.env['fleet.vehicle'].browse(self.context.get('default_vehicle_id'))

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', help="Name of Vehicle.",
                                 track_visibility='onchange', default=_default_vehicle_id_closing)
    reason = fields.Char(string='Reason', required=True)
    # fuel level
    fuel_level = fields.Selection([('0', 'Empty'),
                                   ('8', 'Full'),
                                   ('1', '1/8'),
                                   ('2', '2/8'),
                                   ('3', '3/8'),
                                   ('4', '4/8'),
                                   ('5', '5/8'),
                                   ('6', '6/8'),
                                   ('7', '7/8')],
                                  string='Fuel Level', readonly=False,
                                  related='vehicle_id.fuel_level', required=True)
    # dents
    hood_dent = fields.Boolean(string="Hood", related='vehicle_id.hood_dent', default=True)
    front_r_door_dent = fields.Boolean(string="Front Door (R)", related='vehicle_id.front_r_door_dent', default=True)
    front_l_door_dent = fields.Boolean(string="Front Door (L)", related='vehicle_id.front_l_door_dent', default=True)
    back_r_door_dent = fields.Boolean(string="Back Door (R)", related='vehicle_id.back_r_door_dent', default=True)
    back_l_door_dent = fields.Boolean(string="Back Door (L)", related='vehicle_id.back_l_door_dent', default=True)
    boot_dent = fields.Boolean(string="Boot", related='vehicle_id.boot_dent', default=True)
    # dent charges
    hood_dent_cost = fields.Float(string="Hood", related='vehicle_id.hood_dent_cost')
    front_r_door_dent_cost = fields.Float(string="Front Door (R)", related='vehicle_id.front_r_door_dent_cost')
    front_l_door_dent_cost = fields.Float(string="Front Door (L)", related='vehicle_id.front_l_door_dent_cost')
    back_r_door_dent_cost = fields.Float(string="Back Door (R)", related='vehicle_id.back_r_door_dent_cost')
    back_l_door_dent_cost = fields.Float(string="Back Door (L)", related='vehicle_id.back_l_door_dent_cost')
    boot_dent_cost = fields.Float(string="Boot", related='vehicle_id.boot_dent_cost')
    # dent count
    hood_dent_count = fields.Integer(string="Hood", related='vehicle_id.hood_dent_count')
    front_r_door_dent_count = fields.Integer(string="  Front Door (R)", related='vehicle_id.front_r_door_dent_count')
    front_l_door_dent_count = fields.Integer(string="Front Door (L)", related='vehicle_id.front_l_door_dent_count')
    back_r_door_dent_count = fields.Integer(string="Back Door (R)", related='vehicle_id.back_r_door_dent_count')
    back_l_door_dent_count = fields.Integer(string="Back Door (L)", related='vehicle_id.back_l_door_dent_count')
    boot_dent_count = fields.Integer(string="Boot", related='vehicle_id.boot_dent_count')

    hood_dent_count_new = fields.Integer(string="Hood")
    front_r_door_dent_count_new = fields.Integer(string="Front Door (R)")
    front_l_door_dent_count_new = fields.Integer(string="Front Door (L)")
    back_r_door_dent_count_new = fields.Integer(string="Back Door (R)")
    back_l_door_dent_count_new = fields.Float(string="Back Door (L)")
    boot_dent_count_new = fields.Integer(string="Boot")

    # scratches
    hood_scratch = fields.Boolean(string="Hood", related='vehicle_id.hood_scratch', default=True)
    front_r_door_scratch = fields.Boolean(string="Front Door (R)", related='vehicle_id.front_r_door_scratch', default=True)
    front_l_door_scratch = fields.Boolean(string="Front Door (L)", related='vehicle_id.front_l_door_scratch', default=True)
    back_r_door_scratch = fields.Boolean(string="Back Door (R)", related='vehicle_id.back_r_door_scratch', default=True)
    back_l_door_scratch = fields.Boolean(string="Back Door (L)", related='vehicle_id.back_l_door_scratch', default=True)
    boot_scratch = fields.Boolean(string="Boot", related='vehicle_id.boot_scratch', default=True)
    # scratch charges
    hood_scratch_cost = fields.Float(string="Hood", related='vehicle_id.hood_scratch_cost')
    front_r_door_scratch_cost = fields.Float(string="Front Door (R)", related='vehicle_id.front_r_door_scratch_cost')
    front_l_door_scratch_cost = fields.Float(string="Front Door (L)", related='vehicle_id.front_l_door_scratch_cost')
    back_r_door_scratch_cost = fields.Float(string="Back Door (R)", related='vehicle_id.back_r_door_scratch_cost')
    back_l_door_scratch_cost = fields.Float(string="Back Door (L)", related='vehicle_id.back_l_door_scratch_cost')
    boot_scratch_cost = fields.Float(string="Boot", related='vehicle_id.boot_scratch_cost')
    # scratch count
    hood_scratch_count = fields.Integer(string="Hood", related='vehicle_id.hood_scratch_count')
    front_r_door_scratch_count = fields.Integer(string="Front Door (R)", related='vehicle_id.front_r_door_scratch_count')
    front_l_door_scratch_count = fields.Integer(string="Front Door (L)", related='vehicle_id.front_l_door_scratch_count')
    back_r_door_scratch_count = fields.Integer(string="Back Door (R)", related='vehicle_id.back_r_door_scratch_count')
    back_l_door_scratch_count = fields.Integer(string="Back Door (L)", related='vehicle_id.back_l_door_scratch_count')
    boot_scratch_count = fields.Integer(string="Boot", related='vehicle_id.boot_scratch_count')

    hood_scratch_count_new = fields.Integer(string="Hood")
    front_r_door_scratch_count_new = fields.Integer(string="Front Door (R)")
    front_l_door_scratch_count_new = fields.Integer(string="Front Door (L)")
    back_r_door_scratch_count_new = fields.Integer(string="Back Door (R)")
    back_l_door_scratch_count_new = fields.Integer(string="Back Door (L)")
    boot_scratch_count_new = fields.Integer(string="Boot")

    closing_odometer = fields.Float(string='Closing Odometer',
                                    help='Odometer measure of the vehicle at the moment of this log', required="1")
    return_date = fields.Datetime('Return Date', help="Vehicle returned date.",
                                  required=True, default=lambda s: datetime.now())
    total_damages_cost = fields.Float(string='Total Damages Amount', currency_field='currency_id')
    additional_mileage_cost = fields.Float(string='Additional Usage Charge', currency_field='currency_id')
    total_other_charges_cost = fields.Float(string='Total Other Charges', currency_field='currency_id')
    additional_day_cost = fields.Float(string='Additional Day Charge', currency_field='currency_id')
    additional_fuel_cost = fields.Float(string='Additional Fuel Cost', currency_field='currency_id')
    can_be_invoiced = fields.Boolean(string="Can Be Invoiced?")
    additional_toll_ids = fields.One2many('fleet.vehicle.salik.charges', 'vehicle_return_id',
                                          string='Toll Charge')
    additional_fine_ids = fields.One2many('fleet.vehicle.fine.charges', 'vehicle_return_id',
                                          string='Fine Charge')

    @api.constrains('return_date')
    def check_return_date(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        if tenancy_id.date_start > self.return_date:
            raise ValidationError('Return Date Should Be Greater Than Handover Date.')

    @api.constrains('closing_odometer')
    def check_closing_odometer(self):
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        if tenancy_id.current_odometer > self.closing_odometer:
            raise ValidationError('Closing Odometer Should Be Greater Than Starting Odometer.')

    # @api.multi
    def create_invoice_and_return_vehicle(self):
        rent_obj = self.env['tenancy.rent.schedule']
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        # start_date = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S") strptime(rec.date_start, DT)
        created_rent_obj = rent_obj.create({
            'start_date': datetime.now().strftime(DT),
            'amount': self.total_other_charges_cost + self.additional_mileage_cost + self.total_damages_cost + self.additional_day_cost,
            'vehicle_id': self.vehicle_id.id,
            'tenancy_id': tenancy_id.id,
            'currency_id': tenancy_id.currency_id.id or False,
            'rel_tenant_id': tenancy_id.tenant_id.id or False
        })

        journal_ids = self.env['account.journal'].search(
            [('type', '=', 'sale')])
        if not tenancy_id.vehicle_id.income_acc_id.id:
            raise Warning(_('Please Configure Income Account from Vehicle.'))

        inv_values = {
            'partner_id': tenancy_id and tenancy_id.tenant_id and tenancy_id.tenant_id.id or False,
            'move_type': 'out_invoice',
            'fleet_vehicle_id': tenancy_id.vehicle_id.id or False,
            'date_invoice': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT) or False,
            'journal_id': journal_ids and journal_ids[0].id or False,
            # 'account_id': tenancy_id and tenancy_id.tenant_id.property_account_receivable_id.id or False
        }

        invoice_line_ids_list = []

        if self.total_damages_cost > 0:
            inv_line_total_damages_cost = {
                # 'origin': 'tenancy.rent.schedule',
                'name': 'Vehicle Damages',
                'price_unit': self.total_damages_cost,
                'quantity': 1,
                'account_id': tenancy_id.vehicle_id.income_acc_id.id or False,
                'analytic_account_id': tenancy_id.vehicle_id.analytic_account_id.id or False,
            }
            invoice_line_ids_list.append((0, 0, inv_line_total_damages_cost))

        if self.additional_mileage_cost > 0:
            inv_line_additional_mileage_cost = {
                # 'origin': 'tenancy.rent.schedule',
                'name': 'Extra Usage Charge',
                'price_unit': self.additional_mileage_cost,
                'quantity': 1,
                'account_id': tenancy_id.vehicle_id.income_acc_id.id or False,
                'analytic_account_id': tenancy_id.vehicle_id.analytic_account_id.id or False,
            }
            invoice_line_ids_list.append((0, 0, inv_line_additional_mileage_cost))

        if self.additional_day_cost > 0:
            inv_line_additional_day_cost = {
                # 'origin': 'tenancy.rent.schedule',
                'name': 'Extra Day Usage Charge',
                'price_unit': self.additional_day_cost,
                'quantity': 1,
                'account_id': tenancy_id.vehicle_id.income_acc_id.id or False,
                'analytic_account_id': tenancy_id.vehicle_id.analytic_account_id.id or False,
            }
            invoice_line_ids_list.append((0, 0, inv_line_additional_day_cost))
        # if self.tenancy_id.multi_prop:
        #     for data in self.tenancy_id.prop_id:
        #         for account in data.property_ids.income_acc_id:
        #             inv_line_values.update({'account_id': account.id})

        # if self.tenancy_id.additional_charges and :
        if len(invoice_line_ids_list) > 0:
            inv_values.update({'invoice_line_ids': invoice_line_ids_list})
            acc_id = self.env['account.move'].create(inv_values)
            created_rent_obj.update({'invc_id': acc_id.id, 'inv': True})
        self.vehicle_rent_return()

    # @api.multi
    def vehicle_rent_return(self):
        if self._context.get('active_id', False) and self._context.get('active_model', False):
            for reason in self.env[self._context['active_model']].browse(self._context.get('active_id', False)):
                additional_product_obj = self.env['rental.wizard.fleet.additional.charges']
                salik = fine = 0
                if self.additional_fine_ids:
                    for each in self.additional_fine_ids:
                        new_additional_product = {'additional_charge_product_id': each.fine_product_id.id,
                                                  'unit_measure': each.fine_product_id.uom_id.id,
                                                  'unit_price': each.fine_product_id.lst_price,
                                                  'product_uom_qty': 1,
                                                  'description': each.description + ' - ' + str(each.time_date),
                                                  'cost': each.fine_product_id.lst_price,
                                                  'agreement_id': reason.id}
                        additional_product_obj.create(new_additional_product)
                        salik += each.fine_product_id.lst_price
                if self.additional_toll_ids:
                    for each in self.additional_toll_ids:
                        new_additional_product = {'additional_charge_product_id': each.salik_product_id.id,
                                                  'unit_measure': each.salik_product_id.uom_id.id,
                                                  'unit_price': each.salik_product_id.lst_price,
                                                  'product_uom_qty': 1,
                                                  'description': each.description + ' - ' + str(each.time_date),
                                                  'cost': each.salik_product_id.lst_price,
                                                  'agreement_id': reason.id}
                        additional_product_obj.create(new_additional_product)
                        fine += each.salik_product_id.lst_price
                reason.write({'state': 'return',
                              'duration_cover': self.reason,
                              'closing_odometer': self.closing_odometer,
                              'date': self.return_date,
                              'cancel_by_id': self._uid,
                              'total_other_charges_cost': salik + fine})
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
                                    'state': 'inspection',
                                    'state_id': 6,
                                    'odometer': self.closing_odometer,
                                    'fuel_level': self.fuel_level,
                                    'active_contract': False,})
        tenancy_id = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        return True


class FleetVehicleSalikCharges(models.TransientModel):
    _name = 'fleet.vehicle.salik.charges'

    salik_product_id = fields.Many2one('product.product', string='Product',
                                       required=True,
                                       domain=[('product_tmpl_id.accessories_ok', '=', True)])
    analytic_account_id = fields.Many2one('account.analytic.account', string='Partner')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    unit_price = fields.Float('Unit Price', related='salik_product_id.product_tmpl_id.list_price', readonly=False)
    description = fields.Text(string='Location and Description')
    time_date = fields.Datetime('Toll Date', required=True, default=lambda s: datetime.now())
    vehicle_return_id = fields.Many2one('rent.return.reason')
    vehicle_close_id = fields.Many2one('vehicle.rent.close')


class FleetVehicleFineCharges(models.TransientModel):
    _name = 'fleet.vehicle.fine.charges'

    fine_product_id = fields.Many2one('product.product', string='Product',
                                      required=True, domain=[('product_tmpl_id.accessories_ok', '=', True)])
    vehicle_return_id = fields.Many2one('rent.return.reason')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Partner')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    unit_price = fields.Float('Unit Price', related='fine_product_id.product_tmpl_id.list_price', readonly=False)
    description = fields.Text(string='Location and Description')
    time_date = fields.Datetime('Toll Date', required=True, default=lambda s: datetime.now())
    vehicle_close_id = fields.Many2one('vehicle.rent.close')
