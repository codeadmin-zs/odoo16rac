from odoo import models, api, fields, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import Warning, ValidationError
import logging

_logger = logging.getLogger(__name__)


class RentalOrder(models.Model):
    _inherit = 'sale.order'

    is_rental_order = fields.Boolean("Created In App Rental")
    rental_status = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('waiting', 'Waiting Approval'),
        ('pickup', 'Reserved'),
        ('return', 'Picked-up'),
        ('returned', 'Returned'),
        ('cancel', 'Cancelled'),
    ], string="Rental Status", compute='_compute_rental_status', store=True)
    # rental_status = next action to do basically, but shown string is action done.

    has_pickable_lines = fields.Boolean(compute="_compute_rental_status", store=True)
    has_returnable_lines = fields.Boolean(compute="_compute_rental_status", store=True)
    next_action_date = fields.Datetime(
        string="Rental Next Action Date", compute='_compute_rental_status', store=True)
    has_late_lines = fields.Boolean(compute="_compute_has_late_lines")
    rent_count = fields.Integer(compute='_count_rent', string="Rents")
    rental_wizard_id = fields.Many2one('rental.wizard', 'Rental Wizard', copy=False)
    # start_date = fields.Datetime(
    #     string="Start Date", required=True, help="Rental start date",
    #     default=lambda s: datetime.now().replace() + relativedelta(minute=0, second=0, hours=1))
    # end_date = fields.Datetime(
    #     string="End Date", required=True, help="Rental end date",
    #     default=lambda s: datetime.now().replace() + relativedelta(minute=0, second=0, hours=1, days=1))
    # duration_unit = fields.Selection([("hour", "Hours"), ("day", "Days"),
    #                                   ("week", "Weeks"), ("month", "Months"), ("year", "Years")],
    #                                  string="Duration Unit", required=True, default="day")
    # duration = fields.Integer(
    #     string="Duration", default=1, required=True,
    #     help="Duration of the rental (in unit of the pricing)")
    rental_term = fields.Selection(
        [('short_term', 'Short Term'),
         ('long_term', 'Long Term'), ('spot', 'Spot Rental'),
         ('online', 'Online Booking')],
        string='Rental Type',
        required=True,
        default='long_term', track_visibility='onchange')
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )

    # @api.onchange('start_date')
    # def onchange_start_date(self):
    #     if datetime.strptime(str(self.start_date.replace(microsecond=0)), '%Y-%m-%d %H:%M:%S').date() < \
    #             datetime.now().date():
    #         warning = {
    #             'title': 'Warning',
    #             'message': 'Pick up date should be greater than current date.'
    #         }
    #         return {'warning': warning}
    #
    # @api.onchange('end_date')
    # def onchange_end_date(self):
    #     if datetime.strptime(str(self.start_date.replace(microsecond=0)), '%Y-%m-%d %H:%M:%S').date() > \
    #             datetime.strptime(str(self.end_date.replace(microsecond=0)), '%Y-%m-%d %H:%M:%S').date():
    #         warning = {
    #             'title': 'Warning',
    #             'message': 'End date should be greater than Start date.'
    #         }
    #         return {'warning': warning}
    #     else:
    #         delta = relativedelta(self.end_date, self.start_date)
    #         if delta.years:
    #             self.duration_unit = 'year'
    #             self.duration = delta.years
    #             self.rental_term = 'long_term'
    #         elif delta.months:
    #             self.duration_unit = 'month'
    #             self.duration = delta.months
    #         elif delta.weeks:
    #             self.duration_unit = 'week'
    #             self.duration = delta.weeks
    #         elif delta.days:
    #             self.duration_unit = 'day'
    #             self.duration = delta.days
    #         elif delta.hours:
    #             self.duration_unit = 'hour'
    #             self.duration = delta.hours

    # using from odoo 14's _amount_all, not used odoo 10's _amount_all, getting singleton error
    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.depends('is_rental_order', 'next_action_date', 'rental_status')
    def _compute_has_late_lines(self):
        for order in self:
            order.has_late_lines = (
                    order.is_rental_order
                    and order.rental_status in ['pickup', 'return']  # has_pickable_lines or has_returnable_lines
                    and order.next_action_date < fields.Datetime.now())

    @api.depends('state', 'order_line', 'order_line.product_uom_qty', 'order_line.qty_delivered',
                 'order_line.qty_returned')
    def _compute_rental_status(self):
        # TODO replace multiple assignations by one write?
        for order in self:
            order.is_rental_order = True  # to get the working temporary setting
            if order.state in ['sale', 'done'] and order.is_rental_order:
                rental_order_lines = order.order_line.filtered('is_rental')
                pickeable_lines = rental_order_lines.filtered(lambda sol: sol.qty_delivered < sol.product_uom_qty)
                returnable_lines = rental_order_lines.filtered(lambda sol: sol.qty_returned < sol.qty_delivered)
                min_pickup_date = min(pickeable_lines.mapped('pickup_date')) if pickeable_lines else 0
                min_return_date = min(returnable_lines.mapped('return_date')) if returnable_lines else 0
                if pickeable_lines and (not returnable_lines or min_pickup_date <= min_return_date):
                    order.rental_status = 'pickup'
                    order.next_action_date = min_pickup_date
                elif returnable_lines:
                    order.rental_status = 'return'
                    order.next_action_date = min_return_date
                else:
                    order.rental_status = 'returned'
                    order.next_action_date = False
                order.has_pickable_lines = bool(pickeable_lines)
                order.has_returnable_lines = bool(returnable_lines)
            else:
                order.has_pickable_lines = False
                order.has_returnable_lines = False
                order.rental_status = order.state if order.is_rental_order else False
                order.next_action_date = False

    # PICKUP / RETURN : rental.processing wizard

    def open_pickup(self):
        status = "pickup"
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        lines_to_pickup = self.order_line.filtered(
            lambda r: r.state in ['sale', 'done'] and r.is_rental and float_compare(r.product_uom_qty, r.qty_delivered,
                                                                                    precision_digits=precision) > 0)
        return self._open_rental_wizard(status, lines_to_pickup.ids)

    def open_return(self):
        status = "return"
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        lines_to_return = self.order_line.filtered(
            lambda r: r.state in ['sale', 'done'] and r.is_rental and float_compare(r.qty_delivered, r.qty_returned,
                                                                                    precision_digits=precision) > 0)
        return self._open_rental_wizard(status, lines_to_return.ids)

    def _open_rental_wizard(self, status, order_line_ids):
        context = {
            'order_line_ids': order_line_ids,
            'default_status': status,
            'default_order_id': self.id,
        }
        return {
            'name': _('Validate a pickup') if status == 'pickup' else _('Validate a return'),
            'view_mode': 'form',
            'res_model': 'rental.order.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        if self.is_rental_order:
            return self.env.ref('sale.action_quotations_with_onboarding')
        else:
            return super(RentalOrder, self)._get_portal_return_action()

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', _('New')) == _('New'):
    #         if 'company_id' in vals:
    #             vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('sale.order') or _('New')
    #         else:
    #             vals['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')

    #     # Makes sure partner_invoice_id', 'partner_shipping_id' and 'pricelist_id' are defined
    #     if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
    #         partner = self.env['res.partner'].browse(vals.get('partner_id'))
    #         addr = partner.address_get(['delivery', 'invoice'])
    #         vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
    #         vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
    #         vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
    #     result = super(SaleOrder, self).create(vals)
    #     return result

    # def action_confirm(self):
    #     if self._get_forbidden_state_confirm() & set(self.mapped('state')):
    #         raise UserError(_(
    #             'It is not allowed to confirm an order in the following states: %s'
    #         ) % (', '.join(self._get_forbidden_state_confirm())))
    #
    #     for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
    #         order.message_subscribe([order.partner_id.id])
    #     self.write(self._prepare_confirmation_values())
    #
    #     # Context key 'default_name' is sometimes propagated up to here.
    #     # We don't need it and it creates issues in the creation of linked records.
    #     context = self._context.copy()
    #     context.pop('default_name', None)
    #
    #     self.with_context(context)._action_confirm()
    #     if self.env.user.has_group('sale.group_auto_done_setting'):
    #         self.action_done()
    #     return True

    # @api.multi
    def action_confirm(self):
        self.create_rental()

    def create_rental(self):
        if not self.order_line:
            raise ValidationError('Please enter vehicle details')
        for order in self:
            if order.is_rental_order:
                rental_object = self.env['account.analytic.account']
                booking = False
                for line in self.order_line:
                    wizard_data = line.rental_wizard_id
                    if (wizard_data and order.rental_term != 'long_term') or \
                            (order.rental_term == 'long_term' and wizard_data.license_plate_no):
                        if not wizard_data.license_plate_no:
                            raise Warning(_('Please Select the License Plate for Vehicle(s).'))
                        if len(wizard_data.license_plate_no) > 0:
                            i = 0
                            for lot in wizard_data.license_plate_no:
                                data = {'is_property': True,
                                        # 'new_vehicle_id':lot.id,
                                        'plan_id': 1,
                                        'vehicle_id': lot.id,
                                        'vehicle_id_temp': lot.id,
                                        'date_start': wizard_data.pickup_date,
                                        'date': wizard_data.return_date,
                                        'name': (self.partner_id.name + ' - ' + lot.name),
                                        'sale_order_id': self.id,
                                        'tenant_id': self.partner_id.id,
                                        'manager_id': self.user_id.id,
                                        # 'rent': (line.price_subtotal - wizard_data.additional_charges),
                                        'rent': (line.price_unit - wizard_data.additional_charges),
                                        'duration': wizard_data.duration,
                                        'duration_unit': wizard_data.duration_unit,
                                        'vehicle_lot_id': lot.vehicle_lot_id.id,
                                        'product_id': wizard_data.product_id.id,
                                        'current_odometer': lot.odometer,
                                        'current_odometer_temp': lot.odometer,
                                        'from_sale_order': True,
                                        'rental_terms': self.rental_term,
                                        'invoice_policies': self.invoice_policies_temp}
                                booking = rental_object.create(data)
                                if booking:
                                    state_id = self.env['fleet.vehicle.state'].search([('name', '=', 'Reserved')])
                                    lot.update({'state': "booked", 'state_id': state_id.id})

                                if order.sale_order_option_ids:
                                    additional_product = []
                                    for prods in order.sale_order_option_ids:
                                        item_dict = {
                                            'additional_charge_product_id': prods.product_id.id,
                                            # 'lot_id':i.lot_ids[i].id,
                                            'cost': prods.product_id.lst_price,
                                            'agreement_id': booking.id}
                                        additional_product.append((0, 0, item_dict))
                                    updated_data = {'additional_rental_charges_ids': additional_product}
                                    booking.write(updated_data)
                                    # raise Warning(_('Please Select the License Plate for Vehicle(s).'))
                                    # if len(wizard_data.additional_charges_ids) > 0:
                                    #     for item in wizard_data.additional_charges_ids:
                                    #         msg1 = ("This is my debug message item.lot_ids! %s",item.lot_ids)
                                    #         _logger.error(msg1)
                                    #         if len(item.lot_ids) > 0:
                                    #             item_dict = {
                                    #                   'additional_charge_product_id':item.additional_charge_product_id.id,
                                    #                   'lot_id':item.lot_ids[i].id,
                                    #                   'cost':item.cost,
                                    #                   'agreement_id':booking.id}
                                    #             updated_data = {'additional_rental_charges_ids':[(0,0,item_dict)]}
                                    #             booking.write(updated_data)
                                    # lot_vehicle_id.update({'state':"booked"})
                                i += 1
                        else:
                            raise Warning(_('Please Select the License Plate for Vehicle(s).'))
                            # for item_lot in item.lot_ids:
                            #     additional_charge_dict = {
                            #     'additional_charge_product_id':additional_charge_product_id,agreement_id,cost}
                if booking or self.rental_term == 'long_term':
                    order.state = 'sale'
                    # msg1 = ("This is my debug message lot_vehicle_id! %s",lot_vehicle_id)
                    # _logger.error(msg1)
            else:
                order.state = 'sale'
                # sale.order has no field confirmation_date
                # order.confirmation_date = fields.Datetime.now()
                if self.env.context.get('send_email'):
                    self.force_quotation_send()
                #     sale order line has no function _action_procurement_create in odoo 14
                # order.order_line._action_procurement_create()
        # if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
        #     self.action_done()
        # return True
        context = self._context.copy()
        context.pop('default_name', None)
        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_done()
        return True

    def button_create_rental_contract(self):
        """
        This button method is used to Change Tenancy state to close.
        @param self: The object pointer
        """
        order_lines = self.env['sale.order.line'].search([('order_id', '=', self.id)])
        products = []
        for each in order_lines:
            if each.product_id:
                products.append(each.product_id.id)
        context = {'default_product_id': products}
        return {
            'name': 'Rental Vehicles',
            'res_model': 'sr.multi.product',
            'type': 'ir.actions.act_window',
            'context': context,
            'view_id': False,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new'
        }

    def return_action_to_generate_rental(self):
        """Clean renta def return_action_to_generate_rental(self):l related data if new product cannot be rented."""
        msg1 = "This is my debug message check"
        _logger.error(msg1)
        form = "rental_orders_sale.rental_configurator_view_form"
        context = {
            'default_so_id': self.id}
        # return {"type": "ir.actions.act_window","res_model": "rental.wizard",
        # "views": [[False, "form"]],"view_id": self.env.ref('rental_configurator_view_form').id,
        # 'context': ,"target": "new",}
        return {
            'name': "Rental Form",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'rental.wizard',
            'res_id': self.rental_wizard_id.id,
            'view_id': self.env.ref(form).id,
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }

    # @api.multi
    def _count_rent(self):
        """ This method count the total number of \
        rent for the current vehicle """
        rent_obj = self.env['account.analytic.account']
        for record in self:
            record.rent_count = \
                rent_obj.search_count([('sale_order_id', '=', record.id)])

    # is_rental_order = fields.Boolean("Created In App Rental")
    rent_count = fields.Integer(compute='_count_rent', string="Rents")

    # @api.multi
    def return_action_for_open(self):
        """ This opens the xml view specified in xml_id \
        for the sales order """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            res = self.env['ir.actions.act_window']._for_xml_id('fleet_analytic_accounting.' + xml_id)
            res.update(
                context=dict(self.env.context,
                             default_sale_order_id=self.id, group_by=False),
                domain=[('sale_order_id', '=', self.id)]
            )
            return res
        return False
