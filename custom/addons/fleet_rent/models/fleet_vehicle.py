from odoo import models, fields, api, SUPERUSER_ID, _, exceptions
from datetime import date, datetime
from odoo.exceptions import Warning, UserError, AccessError, ValidationError
from odoo.tools import misc


class FleetVehicle(models.Model):
    """This is the Fleet vehicle model."""
    _inherit = 'fleet.vehicle'

    # @api.multi
    def update_history(self):
        """Method use update color,engine,battery and tire history."""
        wizard_view = ""
        res_model = ""
        view_name = ""
        temp = ""
        cr, uid, context, temp = self.env.args
        context = dict(context)
        if context.get('history', False):
            if context.get("history", False) == "color":
                wizard_view = "update_color_info_form_view"
                res_model = "update.color.info"
                view_name = "Update Color Info"
            elif context.get("history", False) == "engine":
                wizard_view = "update_engine_info_form_view"
                res_model = "update.engine.info"
                view_name = "Update Engine Info"
            elif context.get('history', False) == 'vin':
                wizard_view = "update_vin_info_form_view"
                res_model = "update.vin.info"
                view_name = "Update Vin Info"
            elif context.get('history', False) == 'tire':
                wizard_view = "update_tire_info_form_view"
                res_model = "update.tire.info"
                view_name = "Update Tyre Info"
            elif context.get('history', False) == 'battery':
                wizard_view = "update_battery_info_form_view"
                res_model = "update.battery.info"
                view_name = "Update Battery Info"

        model_data_ids = self.env['ir.model.data'].search([
            ('model', '=', 'ir.ui.view'), ('name', '=', wizard_view)])
        resource_id = model_data_ids.read(['res_id'])[0]['res_id']
        context.update({'vehicle_ids': self._ids})
        self.env.args = cr, uid, misc.frozendict(context)
        return {
            'name': view_name,
            'context': self._context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': res_model,
            'views': [(resource_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    # # @api.constrains('start_date_insurance', 'end_date_insurance')
    ## def check_insurance_end_date(self):
    ##     for vehicle in self:
    # #        if vehicle.start_date_insurance and vehicle.end_date_insurance:
    #  #           if vehicle.end_date_insurance < vehicle.start_date_insurance:
    # #                 raise ValidationError('Insurance End Date Should Be \
    # #                     Greater Than Start Date.')
    # #
    # # @api.constrains('start_date_insurance', 'acquisition_date')
    # # def check_insurance_start_date(self):
    # #     for vehicle in self:
    # #         if vehicle.start_date_insurance and vehicle.acquisition_date:
    # #             if vehicle.start_date_insurance < vehicle.acquisition_date:
    # #                 raise ValidationError('Insurance Start Date Should Be \
    # #                     Greater Than Registration Date.')




    @api.depends('vehicle_lot_id')
    def _get_vehicle_down_payment(self):
        for record in self:
            if record.vehicle_lot_id:
                move_id = self.env['stock.move.line'].search([('lot_id', '=', record.vehicle_lot_id.id)],
                                                             limit=1).move_id

                if move_id:
                    purchase_line_id = self.env['stock.move'].search([('id', '=', move_id.id)]).purchase_line_id

                if purchase_line_id:
                    record.vehicle_cost_price = purchase_line_id.price_unit
                    invoice_line_obj = self.env['account.move.line'].search(
                        [('purchase_line_id', '=', purchase_line_id.id), ('move_id.state', 'in', ['open', 'paid'])],
                        limit=1, order="id asc")
                    # if invoice_line_obj:
                    #     price_subtotal = invoice_line_obj.price_subtotal
                    #     quantity = invoice_line_obj.quantity
                    #     record.down_payment = price_subtotal / quantity
                    # else:
                    #     record.down_payment = 0
                else:
                    record.vehicle_cost_price = 0


    @api.depends('name')
    def _compute_admin_is_user(self):
        if self.env.user.has_group('base.user_admin'):
            self.current_user_admin = True
        else:
            self.current_user_admin = False

    # @api.depends('model_id', 'license_plate', 'vin_sn')
    # def _compute_vehicle_name(self):
    #     for record in self:
    #         # msg1 = ("This is my debug message 1!")
    #         # _logger.error(msg1)
    #         if record.model_id and record.model_id.brand_id:
    #             lic_plate = record.license_plate
    #             vin_sn = record.vin_sn
    #             if not record.license_plate:
    #                 lic_plate = ''
    #             if not record.vin_sn:
    #                 vin_sn = ''
    #             record.name = \
    #                 record.model_id.brand_id.name + '/' + \
    #                 record.model_id.name + '/' + lic_plate + '/' + vin_sn
    #         elif record.vin_sn and not record.model_id and not record.model_id.brand_id:
    #             record.name = record.vin_sn
    #         else:
    #             record.name = ''

    # @api.model
    # def create(self, vals):
    #     print(self)
    #     if vals.get('name_seq', 'New') == 'New':
    #         vals['name_seq'] = self['ir.sequence'].next_by_code('fleet.vehicle.sequence') or 'New'
    #     result = super(FleetVehicle, self).create(vals)
    #     return result


    @api.depends('f_brand_id', 'model_id', 'license_plate', 'vin_sn', 'finished_registration',
                 'submitted_registration')
    def _compute_approval_ready_status(self):
        for record in self:
            # msg1 = ("This is my debug message 1!")
            # _logger.error(msg1)
            if record.model_id and record.f_brand_id and record.license_plate and record.vin_sn and record.submitted_registration != True and record.finished_registration != True:
                record.ready_for_approval = True
            else:
                record.ready_for_approval = False

    @api.onchange('payment')
    def _compute_total_payment(self):
        total_insurance_payment = (self.vehicle_cost_price * self.payment) / 100

    # # @api.onchange('odo_meter_increment_ids')
    # # def checking(self):
    # #     print('herererererererererer')
    # #     pprint.pprint(self.env.context)
    #
    #   # @api.depends('finished_registration')
    #  # def change_location(self):
    #  #

    vehicle_lot_id = fields.Many2one('stock.lot', string='Lot ID', required=True)
    vehicle_prodcut_template_id = fields.Many2one('product.template', string='Product Template', required=True)
    vehicle_type_str = fields.Char(string='vehicle type')
    vehicle_prodcut_id = fields.Many2one('product.product', string='Product Variant', required=True)
    vehicle_type_str = fields.Char(string='vehicle type')
    vin_sn = fields.Char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)',
                         copy=False)
    engine_no = fields.Char('Engine Number', )
    income_acc_id = fields.Many2one("account.account",
                                    string="Income Account")
    expence_acc_id = fields.Many2one("account.account",
                                     string="Expense Account")
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    asset_id = fields.Many2one('account.asset.asset', string='Asset')
    f_brand_id = fields.Many2one('fleet.vehicle.model.brand', string='Make')
    model_no = fields.Char(string='Model No', translate=True)

    # name = fields.Char(compute="_compute_vehicle_name", store=True,
    #                    string='Fleet ID')
    name_seq = fields.Char(string='Fleet ID', copy=False, readonly=True,
                           default=lambda self: self.env['ir.sequence'].next_by_code('fleet.vehicle.sequence'))
    current_user_admin = fields.Boolean('Current User is Admin', default=False, compute='_compute_admin_is_user')
    fuel_type = fields.Many2one('fleet.category.vehicle.fuel', string='Fuel', store=True,
                                related='model_id.category_vehicle_fuel_id')
    vechical_type_id = fields.Many2one('vehicle.type', string='Vehicle Type')
    state = fields.Selection([('draft', 'Draft'),
                              ('booked', 'Reserved'),
                              ('waiting', 'Waiting Approval'),
                              ('inspection', 'Available'),
                              ('in_progress', 'In Service'),
                              ('contract', 'On Contract'),
                              ('rent', 'On Rent'),
                              ('complete', 'Completed'),
                              ('accident', 'Accident'),
                              ('replacement', 'Replacement'),
                              ('released', 'Released'),
                              ('write-off', 'Total Loss')],
                             string='State', default='draft', track_visibility='onchange')

    down_payment = fields.Float("Down payment", compute='_get_vehicle_down_payment')

    vehicle_cost_price = fields.Float("Purchase price", compute='_get_vehicle_down_payment')
    submitted_registration = fields.Boolean(string="Vehicle Submitted for Approval", copy=False)
    ready_for_approval = fields.Boolean(string="Vehicle Ready For Approval", compute="_compute_approval_ready_status",
                                        copy=False)
    # vehical_division_id = fields.Many2one('vehicle.divison', string='Division')
    vechical_location_id = fields.Many2one('res.country.state',
                                           string='Registration State')
    finished_registration = fields.Boolean(string="Vehicle Registration Finished", copy=False)
    vehicle_type_image = fields.Binary(string='Vehicle Type Image')

    released_date = fields.Date(string='Released Date', readonly=True, default=fields.Date.today)

    reg_id = fields.Many2one('res.users', string='Registered By')
    updated_by = fields.Many2one('res.users', string='Updated By')
    updated_date = fields.Date(string='Updated date')
    warranty_period = fields.Date(string='Warranty Upto')
    warranty_period_km = fields.Char()
    last_service_date = fields.Date(string='Last Service', readonly=True)
    last_change_status_date = fields.Date(string='Last Status Changed Date',
                                          readonly=True)
    last_service_by_id = fields.Many2one('res.partner',
                                         string="Last Service By")
    work_order_ids = fields.One2many('fleet.vehicle.log.services',
                                     'vehicle_id', string='Work Order')
    work_order_close = fields.Boolean(string='Work Order Close', default=True)
    next_service_date = fields.Date(string='Next Service', readonly=True)
    fmp_id_editable = fields.Boolean(string='Vehicle ID Editable?')
    main_type = fields.Selection([('vehicle', 'Vehicle'),
                                  ('non-vehicle', 'Non-Vehicle')],
                                 default='vehicle', string='Main Type')
    ## next_service_date_ids = fields.One2many('next.service.days', 'vehicle_id', string='Next Date For Service')
    ## due_odometer = fields.Float(string='Next Service Odometer', readonly=True)
    ## due_odometer_unit = fields.Selection([('kilometers', 'Kilometers'),
    ##                                       ('miles', 'Miles')],
    ##                                      string='Odometer Unit',
    ##                                      help='Unit of the odometer ')
    ## pending_repair_type_ids = fields.One2many('pending.repair.type',
    ##                                           'vehicle_rep_type_id',
    ##                                           string='Pending Repair Types',
    ##                                           readonly=True)

    insurance_company_id = fields.Many2one('res.partner',
                                           string='Insurance Company',
                                           domain=[('insurance', '=', True)])
    insurance_type_id = fields.Many2one('insurance.type',
                                        string='Insurance Type')

    ## start_date_insurance = fields.Date(string='Start Date')
    ## end_date_insurance = fields.Date(string='End Date')
    policy_number = fields.Char(string='Policy Number', size=32)
    payment = fields.Float(string='Amount', compute='pay_to_percent')
    payment_in_percent = fields.Integer(string='Payment in %')
    service_interval = fields.Char(string='Service Due')
    ## payment_deduction = fields.Float(string='Deduction')

    fleet_attach_ids = fields.One2many('ir.attachment', 'attachment_id',
                                       string='Attachments')
    is_color_set = fields.Boolean(string='Is Color Set?')
    is_engine_set = fields.Boolean(string='Is Engine Set')
    is_vin_set = fields.Boolean(string='Is Vin Set?')
    is_tire_size_set = fields.Boolean(string='Is Tire Size set?')
    is_tire_srno_set = fields.Boolean(string='Is Tire Srno set?')
    is_tire_issue_set = fields.Boolean(string='Is Tire Issue set?')
    is_battery_size_set = fields.Boolean(string='Is battery Size set?')
    is_battery_srno_set = fields.Boolean(string='Is battery Srno set?')
    is_battery_issue_set = fields.Boolean(string='Is battery Issue set?')
    engine_history_ids = fields.One2many('engine.history', 'vehicle_id',
                                         string="Engine History",
                                         readonly=True)
    vin_history_ids = fields.One2many('vin.history', 'vehicle_id',
                                      string="Vin History", readonly=True)
    color_history_ids = fields.One2many('color.history', 'vehicle_id',
                                        string="Color History", readonly=True)
    tire_history_ids = fields.One2many('tire.history', 'vehicle_id',
                                       string="Tire History", readonly=True)
    battery_history_ids = fields.One2many('battery.history', 'vehicle_id',
                                          string="Battery History",
                                          readonly=True)
    active_contract = fields.Many2one('account.analytic.account', 'Active Rental Contract')
    description = fields.Text(string='About Vehicle', translate=True)

    ## odo_meter_increment_ids = fields.One2many('next.increment.number', 'vehicle_id',
    ##                                           string='Odo Meter Increment For Service')

    # dents
    hood_dent = fields.Boolean(string="Hood", default=True)
    front_r_door_dent = fields.Boolean(string="Front Door (R)", default=True)
    front_l_door_dent = fields.Boolean(string="Front Door (L)", default=True)
    back_r_door_dent = fields.Boolean(string="Back Door (R)", default=True)
    back_l_door_dent = fields.Boolean(string="Back Door (L)", default=True)
    boot_dent = fields.Boolean(string="Boot", default=True)
    # dent charges
    hood_dent_cost = fields.Float(string="Hood")
    front_r_door_dent_cost = fields.Float(string="Front Door (R)")
    front_l_door_dent_cost = fields.Float(string="Front Door (L)")
    back_r_door_dent_cost = fields.Float(string="Back Door (R)")
    back_l_door_dent_cost = fields.Float(string="Back Door (L)")
    boot_dent_cost = fields.Float(string="Boot")
    # dent count
    hood_dent_count = fields.Integer(string="Hood")
    front_r_door_dent_count = fields.Integer(string="Front Door (R)")
    front_l_door_dent_count = fields.Integer(string="Front Door (L)")
    back_r_door_dent_count = fields.Integer(string="Back Door (R)")
    back_l_door_dent_count = fields.Integer(string="Back Door (L)")
    boot_dent_count = fields.Integer(string="Boot")

    hood_dent_count_new = fields.Integer(string="Hood")
    front_r_door_dent_count_new = fields.Integer(string="Front Door (R)")
    front_l_door_dent_count_new = fields.Integer(string="Front Door (L)")
    back_r_door_dent_count_new = fields.Integer(string="Back Door (R)")
    back_l_door_dent_count_new = fields.Integer(string="Back Door (L)")
    boot_dent_count_new = fields.Integer(string="Boot")

    # scratches
    hood_scratch = fields.Boolean(string="Hood", default=True)
    front_r_door_scratch = fields.Boolean(string="Front Door (R)", default=True)
    front_l_door_scratch = fields.Boolean(string="Front Door (L)", default=True)
    back_r_door_scratch = fields.Boolean(string="Back Door (R)", default=True)
    back_l_door_scratch = fields.Boolean(string="Back Door (L)", default=True)
    boot_scratch = fields.Boolean(string="Boot", default=True)
    # scratch scratches
    hood_scratch_cost = fields.Float(string="Hood")
    front_r_door_scratch_cost = fields.Float(string="Front Door (R)")
    front_l_door_scratch_cost = fields.Float(string="Front Door (L)")
    back_r_door_scratch_cost = fields.Float(string="Back Door (R)")
    back_l_door_scratch_cost = fields.Float(string="Back Door (L)")
    boot_scratch_cost = fields.Float(string="Boot")
    # scratch scratches
    hood_scratch_count = fields.Integer(string="Hood")
    front_r_door_scratch_count = fields.Integer(string="Front Door (R)")
    front_l_door_scratch_count = fields.Integer(string="Front Door (L)")
    back_r_door_scratch_count = fields.Integer(string="Back Door (R)")
    back_l_door_scratch_count = fields.Integer(string="Back Door (L)")
    boot_scratch_count = fields.Integer(string="Boot")

    hood_scratch_count_new = fields.Integer(string="Hood")
    front_r_door_scratch_count_new = fields.Integer(string="Front Door (R)")
    front_l_door_scratch_count_new = fields.Integer(string="Front Door (L)")
    back_r_door_scratch_count_new = fields.Integer(string="Back Door (R)")
    back_l_door_scratch_count_new = fields.Integer(string="Back Door (L)")
    boot_scratch_count_new = fields.Integer(string="Boot")
    # Fuel
    fuel_level = fields.Selection([('0', 'Empty'),
                                   ('8', 'Full'),
                                   ('1', '1/8'),
                                   ('2', '2/8'),
                                   ('3', '3/8'),
                                   ('4', '4/8'),
                                   ('5', '5/8'),
                                   ('6', '6/8'),
                                   ('7', '7/8')], string='Fuel Level', default='8')

    @api.constrains('warranty_period_km')
    def _check_warranty_period_km(self):
        for record in self:
            try:
                odo_km = int(record.warranty_period_km)
                # if model_y < 1900 or model_y > datetime.now().year:
                #     raise exceptions.ValidationError("Invalid year. Please enter a 4-digit year.")
            except:
                raise exceptions.ValidationError("Invalid digit. Please enter a valid Km in digit.")
    @api.onchange('payment_in_percent')
    def pay_to_percent(self):
        comp_val = (self.payment_in_percent / 100) * self.vehicle_cost_price
        self.payment = comp_val

    @api.model
    def create(self, vals):
        # if not vals.get('model_id', False):
        #     raise Warning(_('Model is not selected for this vehicle!'))
        vals.update({'fmp_id_editable': True})
        seq = self.env['ir.sequence'].next_by_code('fleet.vehicle')
        vals.update({'name': seq})
        if self._uid:
            vals.update({'reg_id': self._uid})
        if not vals.get('acquisition_date', False):
            vals.update({'acquisition_date': date.today()})
        if not vals.get('last_change_status_date', False):
            vals.update({'last_change_status_date': date.today()})

        # checking once vin, color and engine number will be set than field
        # automatically become readonly.
        # if vals.get('odometer_unit'):
        #     vals.update({'odometer_check': False})
        if vals.get('vin_sn', False):
            vals.update({'is_vin_set': True})
        if vals.get('vehical_color_id', False):
            vals.update({'is_color_set': True})
        if vals.get('engine_no', False):
            vals.update({'is_engine_set': True})
        if vals.get('tire_size', False):
            vals.update({'is_tire_size_set': True})
        if vals.get('tire_srno', False):
            vals.update({'is_tire_srno_set': True})
        if vals.get('tire_issuance_date', False):
            vals.update({'is_tire_issue_set': True})

        if vals.get('battery_size', False):
            vals.update({'is_battery_size_set': True})
        if vals.get('battery_srno', False):
            vals.update({'is_battery_srno_set': True})
        if vals.get('battery_issuance_date', False):
            vals.update({'is_battery_issue_set': True})
        return super(FleetVehicle, self).create(vals)

    # @api.multi
    def button_submit_for_approval(self):
        state = self.env['fleet.vehicle.state'].search([('name', '=', 'Registered')])

        return self.write({'state': 'waiting',
                           'submitted_registration': True,
                           'finished_registration': False,
                           'state_id': state.id
                           })

    ## def add_service_days(self):
    ##     return self.write({'next_service_date_ids': [(0, 0, self.next_service_date_ids.id)],
    ##                        'odo_meter_increment_ids': [(0, 0, self.odo_meter_increment_ids.id)]})

    ## @api.multi
    def button_approve_vehicle(self):
        state = self.env['fleet.vehicle.state'].search([('name', '=', 'Available')])
        # raise ValidationError('Debug_Error')
        return self.write({'state': 'inspection',
                           'finished_registration': True,
                           'submitted_registration': False,
                           'state_id': state.id
                           })
