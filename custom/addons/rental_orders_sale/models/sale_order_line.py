from odoo import models, fields, api, sql_db, _, tools
from odoo.exceptions import Warning, except_orm, ValidationError
from datetime import datetime, timedelta
from babel.dates import format_datetime, format_date
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_rental = fields.Boolean(default=False)  # change to compute if pickup_date and return_date set?
    is_rental_order = fields.Boolean("Created In App Rental", related='order_id.is_rental_order')
    qty_returned = fields.Float("Returned", default=0.0, copy=False)

    pickup_date = fields.Datetime(string="Pickup")
    return_date = fields.Datetime(string="Return")
    reservation_begin = fields.Datetime("Pickup date - padding time", compute='_compute_reservation_begin', store=True)

    is_late = fields.Boolean(string="Is overdue", compute="_compute_is_late",
                             help="The products haven't been returned in time")

    # is_product_rentable = fields.Boolean(related='product_id.rent_ok')
    rental_updatable = fields.Boolean(compute='_compute_rental_updatable')
    rental_wizard_id = fields.Many2one('rental.wizard', 'Rental Wizard', copy=False)

    duration = fields.Integer(
        string="Duration", default=1, help="Duration of the rental (in unit of the pricing)")
    duration_unit = fields.Selection([("hour", "Hours"), ("day", "Days"), ("week", "Weeks"), ("month", "Months")],
                                     string="Duration Unit")

    lot_state = fields.Selection([('lot_not_added', 'VIN not added'), ('lot_added', 'VIN added')], string='Status',
                                 default='lot_not_added')

    # TODO use is_product_rentable in rental_configurator_widget instead of rpc call?

    @api.depends('return_date')
    def _compute_is_late(self):
        now = fields.Datetime.now()
        for line in self:
            # By default, an order line is considered late only if it has one hour of delay
            line.is_late = line.return_date and line.return_date + timedelta(hours=self.company_id.min_extra_hour) < now

    @api.depends('pickup_date')
    def _compute_reservation_begin(self):
        lines = self.filtered(lambda line: line.is_rental)
        for line in lines:
            line.reservation_begin = line.pickup_date
            # test_var = self - lines
            # msg1 = ("This is my debug message line.test_var! %s",test_var)
            # _logger.error(msg1)
        #(self - lines).reservation_begin = None

    @api.depends('state', 'qty_invoiced', 'qty_delivered')
    def _compute_rental_updatable(self):
        rental_lines = self.filtered('is_rental')
        sale_lines = self - rental_lines
        for line in sale_lines:
            line.rental_updatable = line.product_updatable
        rental_lines.write({'rental_updatable': True})
        # for line in rental_lines:
        #     if line.state == 'cancel' or (line.state in ['sale', 'done'] and (line.qty_invoiced > 0 or line.qty_delivered > 0)):
        #         line.rental_updatable = False
        #     else:
        #         line.rental_updatable = True

    # @api.onchange('product_id')
    # def product_id_change(self):
    #     """Clean rental related data if new product cannot be rented."""
    #     print(self)
    #     # if (not self.is_product_rentable) and self.is_rental:
    #     #     self.update({
    #     #         'is_rental': False,
    #     #         'pickup_date': False,
    #     #         'return_date': False,
    #     #     })
    #     warning = {}
    #     if self.product_id.rent_ok and self.product_id.fleet_ok:
    #         # for line in self:
    #         #   line_id = line.id
    #         so_id = self.env.context.get('so_id')
    #         msg1 = ("This is my debug message self._origin.order_id.id! %s",so_id)
    #         _logger.error(msg1)
    #         # msg1 = ("This is my debug message is_product_rentable! %s",self.is_product_rentable)
    #         # _logger.error(msg1)
    #         # msg1 = ("This is my debug message is_rental! %s",self.is_rental)
    #         # _logger.error(msg1)
    #         # msg1 = ("This is my debug message pickup_date! %s",self.pickup_date)
    #         # _logger.error(msg1)
    #         # msg1 = ("This is my debug message return_date! %s",self.return_date)
    #         # _logger.error(msg1)
    #         context = {'default_product_id': self.product_id.id,
    #                    'default_rental_order_line_id': self.id,
    #                    'default_so_id': self.order_id.id}
    #         # return {
    #         #     'warning':
    #         #     {
    #         #         'title': _('Info'),
    #         #         'message': _('Rental Rates'),
    #         #         'action': {
    #         #                    "type": "ir.actions.act_window",
    #         #                    "res_model": "rental.wizard",
    #         #                    "views": [[False, "form"]],
    #         #                    "view_id": self.env.ref('rental_orders_sale.rental_configurator_view_form').id,
    #         #                    'context': context,
    #         #                    "target": "new",
    #         #                 },
    #         #     },
    #         # }
    #         s = self.return_action_to_generate_rental()
    #         print(s)
    #         return s

    # TODO use is_product_rentable in rental_configurator_widget instead of rpc call?

    def delete_order_line(self):
        for order in self:
            order.unlink()

    # @api.multi
    def return_action_to_generate_rental(self):
        """Clean rental related data if new product cannot be rented."""
        msg1 = "This is my debug message check"
        _logger.error(msg1)
        form = "rental_orders_sale.rental_configurator_view_form"
        # context = {'default_product_id': self.product_id.id,
        #            'default_rental_order_line_id': self.id,
        #            'default_so_id': self.order_id.id}
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
          'context': self._context,
          'target': 'new',
        }

    @api.onchange('qty_delivered')
    def _onchange_qty_delivered(self):
        """When picking up more than reserved, reserved qty is updated"""
        if self.qty_delivered > self.product_uom_qty:
            self.product_uom_qty = self.qty_delivered

    @api.onchange('pickup_date', 'return_date')
    def _onchange_rental_info(self):
        """Trigger description recomputation"""
        self.product_id_change()

    @api.onchange('is_rental')
    def _onchange_is_rental(self):
        if self.is_rental and not self.order_id.is_rental_order:
            self.order_id.is_rental_order = True

    _sql_constraints = [
        ('rental_stock_coherence',
         "CHECK(NOT is_rental OR qty_returned <= qty_delivered)",
         "You cannot return more than what has been picked up."),
        # ('rental_period_coherence',
        #     "CHECK(NOT is_rental OR pickup_date < return_date)",
        #     "Please choose a return date that is after the pickup date."),
        ('rental_period_coherence',
         "CHECK(1 = 1)",
         "Please choose a return date that is after the pickup date."),
    ]

    def get_sale_order_line_multiline_description_sale(self, product):
        """Add Rental information to the SaleOrderLine name."""
        name = super(RentalOrderLine, self).get_sale_order_line_multiline_description_sale(product)
        if self.order_id.rental_rank:
            # name1 = product.product_tmpl_id.brand_id.name + ' ' + product.product_tmpl_id.model_id.name,
            name1 = self.product_id.product_tmpl_id.name
            if name1:
                return name1 + self.get_rental_order_line_description()
        return name + self.get_rental_order_line_description()

    def get_rental_order_line_description(self):
        if (self.is_rental):
            if self.pickup_date.date() == self.return_date.date():
                # If return day is the same as pickup day, don't display return_date Y/M/D in description.
                return_date_part = tools.format_datetime(self.with_context(use_babel=True).env, self.return_date,
                                                         tz=self.env.user.tz, dt_format='h:mm a')
            else:
                return_date_part = tools.format_datetime(self.with_context(use_babel=True).env, self.return_date,
                                                         tz=self.env.user.tz, dt_format='short')

            return "\n%s %s %s" % (
                tools.format_datetime(self.with_context(use_babel=True).env, self.pickup_date, self.env.user.tz,
                                      dt_format='short'),
                _("to"),
                return_date_part,
            )
        else:
            return ""

    def _get_display_price(self, product):
        """Ensure unit price isn't recomputed."""
        if self.is_rental:
            return self.price_unit
        else:
            return super(RentalOrderLine, self)._get_display_price(product)

    def _generate_delay_line(self, qty):
        """Generate a sale order line representing the delay cost due to the late return.

        :param float qty:
        :param timedelta duration:
        """
        self.ensure_one()
        if qty <= 0 or not self.is_late:
            return

        duration = fields.Datetime.now() - self.return_date

        delay_price = self.product_id._compute_delay_price(duration)
        if delay_price <= 0.0:
            return

        # migrate to a function on res_company get_extra_product?
        delay_product = self.company_id.extra_product
        if not delay_product:
            delay_product = self.env['product.product'].with_context(active_test=False).search(
                [('default_code', '=', 'RENTAL'), ('type', '=', 'service')], limit=1)
            if not delay_product:
                delay_product = self.env['product.product'].create({
                    "name": "Rental Delay Cost",
                    "standard_price": 0.0,
                    "type": 'service',
                    "default_code": "RENTAL",
                    "purchase_ok": False,
                })
                # Not set to inactive to allow users to put it back in the settings
                # In case they removed it.
            self.company_id.extra_product = delay_product

        if not delay_product.active:
            return

        delay_price = self.product_id.currency_id._convert(
            from_amount=delay_price,
            to_currency=self.currency_id,
            company=self.company_id,
            date=date.today(),
        )

        vals = self._prepare_delay_line_vals(delay_product, delay_price, qty)

        self.order_id.write({
            'order_line': [(0, 0, vals)]
        })

    def _prepare_delay_line_vals(self, delay_product, delay_price, qty):
        """Prepare values of delay line.

        :param float delay_price:
        :param float quantity:
        :param delay_product: Product used for the delay_line
        :type delay_product: product.product
        :return: sale.order.line creation values
        :rtype dict:
        """
        delay_line_description = self._get_delay_line_description()
        return {
            'name': delay_line_description,
            'product_id': delay_product.id,
            'product_uom_qty': qty,
            'product_uom': self.product_id.uom_id.id,
            'qty_delivered': qty,
            'price_unit': delay_price,
        }

    def _get_delay_line_description(self):
        # Shouldn't tz be taken from self.order_id.user_id.tz ?
        return "%s\n%s: %s\n%s: %s" % (
            self.product_id.name,
            _("Expected"),
            tools.format_datetime(self.with_context(use_babel=True).env, self.pickup_date, tz=self.env.user.tz,
                            dt_format='short'),
            _("Returned"),
            tools.format_datetime(self.with_context(use_babel=True).env, fields.Datetime.now(), tz=self.env.user.tz,
                            dt_format='short')
        )

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'duration')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = (line.price_unit * line.duration) * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
