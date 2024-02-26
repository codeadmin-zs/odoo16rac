from odoo import models, _, fields
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class PurchaseOrderLineExtend(models.Model):
    _inherit = 'purchase.order.line'

    def _get_product_purchase_description(self, product_lang):
        name = super(PurchaseOrderLineExtend, self)._get_product_purchase_description(product_lang)
        name1 = product_lang.product_template_attribute_value_ids.product_attribute_value_id.name
        if name1:
            return name1
        return name


class PickingType(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # Sanity checks.
        pickings_without_moves = self.browse()
        pickings_without_quantities = self.browse()
        pickings_without_lots = self.browse()
        products_without_lots = self.env['product.product']
        for picking in self:
            # if not picking.move_lines and not picking.move_line_ids: (move_lines changed to move_ids in odoo16)
            if not picking.move_ids and not picking.move_line_ids:
                pickings_without_moves |= picking

            picking.message_subscribe([self.env.user.partner_id.id])
            picking_type = picking.picking_type_id
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            no_quantities_done = all(
                float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in
                picking.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
            no_reserved_quantities = all(
                # product_qty is change to reserved_qty
                float_is_zero(move_line.reserved_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line
                in picking.move_line_ids)
            if no_reserved_quantities and no_quantities_done:
                pickings_without_quantities |= picking

            if picking_type.use_create_lots or picking_type.use_existing_lots:
                lines_to_check = picking.move_line_ids
                if not no_quantities_done:
                    lines_to_check = lines_to_check.filtered(
                        lambda line: float_compare(line.qty_done, 0, precision_rounding=line.product_uom_id.rounding))
                for line in lines_to_check:
                    product = line.product_id
                    if product and product.tracking != 'none':
                        if not line.lot_name and not line.lot_id:
                            pickings_without_lots |= picking
                            products_without_lots |= product

        if not self._should_show_transfers():
            if pickings_without_moves:
                raise UserError(_('Please add some items to move.'))
            if pickings_without_quantities:
                raise UserError(self._get_without_quantities_error_message())
            if pickings_without_lots:
                raise UserError(_('You need to supply a Lot/Serial number for products %s.') % ', '.join(
                    products_without_lots.mapped('display_name')))
        else:
            message = ""
            if pickings_without_moves:
                message += _('Transfers %s: Please add some items to move.') % ', '.join(
                    pickings_without_moves.mapped('name'))
            if pickings_without_quantities:
                message += _(
                    '\n\nTransfers %s: You cannot validate these transfers if no quantities are reserved nor done. To force these transfers, switch in edit more and encode the done quantities.') % ', '.join(
                    pickings_without_quantities.mapped('name'))
            if pickings_without_lots:
                message += _('\n\nTransfers %s: You need to supply a Lot/Serial number for products %s.') % (
                    ', '.join(pickings_without_lots.mapped('name')),
                    ', '.join(products_without_lots.mapped('display_name')))
            if message:
                raise UserError(message.lstrip())

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # Call `_action_done`.
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder = self.browse(self.env.context['picking_ids_not_to_backorder'])
            pickings_to_backorder = self - pickings_not_to_backorder
        else:
            pickings_not_to_backorder = self.env['stock.picking']
            pickings_to_backorder = self
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
        self.do_create_vehicles()
        return True

    def do_create_vehicles(self):
        if self.picking_type_code and self.picking_type_code == 'incoming':
            # msg1 = ("This is my debug message 3!")
            # _logger.error(msg1)
            fleet_object = self.env['fleet.vehicle']
            asset_object = self.env['account.asset.asset']
            analytic_object = self.env['account.analytic.account']
            pack_operations = self.filtered(lambda picking: picking.move_line_ids)
            default_asset_category_id = self.env['account.asset.category'].search([('name', '!=', False)], limit=1).id
            # no_pack_op_pickings.action_done()
            # other_pickings = self - self.filtered(lambda picking: not picking.pack_operation_ids)
            purch_id = self.env['purchase.order'].search([('name', '=', self.origin)])

            for operation in pack_operations.move_line_ids:
                msg1 = ("This is my debug default_asset_category_id! %s", default_asset_category_id)
                _logger.error(msg1)
                product_id = operation.product_id
                if product_id.rent_ok and product_id.fleet_ok and operation.lot_id:
                    # msg1 = ("This is my debug message 5!")
                    # _logger.error(msg1)
                    for lot in operation.lot_id:
                        brand_id_temp = self.env['fleet.vehicle.model'].search(
                            [('id', '=', product_id.product_tmpl_id.model_id_zt.id)])
                        # msg1 = ("This is my debug message 6!")
                        # _logger.error(msg1)
                        brand_id_temp = self.env['fleet.vehicle.model'].search([('id', '=', product_id.product_tmpl_id.model_id_zt.id)])
                        categ_name = self.env['vehicle.category'].search([('id', '=', brand_id_temp.category_vehicle_class_id.id)]).name
                        if lot.name:
                            fleet_data = {'vehicle_lot_id': lot.id,
                                          'odometer_unit': 'kilometers',
                                          'vehicle_type_str': categ_name,
                                          'vehicle_prodcut_template_id': product_id.product_tmpl_id.id,
                                          'vehicle_prodcut_id': product_id.id,
                                          'vin_sn': lot.name,
                                          # 'vehicle_type_str': brand_id_temp.category_vehicle_class_id.name,
                                          'income_acc_id': product_id.property_account_income_id.id,
                                          'expence_acc_id': product_id.property_account_expense_id.id,
                                          'model_id': product_id.product_tmpl_id.model_id_zt.id,
                                          'f_brand_id': product_id.product_tmpl_id.brand_id_zt.id,}

                            vehicle = fleet_object.create(fleet_data)
                            msg1 = ("This is my debug message vehicle! %s", vehicle)
                            _logger.error(msg1)
                            if vehicle.vin_sn:
                                # analytic_account_data = {'is_property':False,
                                #                           'name':vehicle.vin_sn,
                                #                           'state':'draft',
                                #                           'lock_state':'open',
                                #                           'current_odometer':0.0,
                                #                           'duration':1,
                                #                           'duration_unit':'day',
                                # 'invoice_policies':'advanced','company_id':self.env.user.company_id.id,'vehicle_lot_id':lot.lot_id.id}

                                data = {'company_id': self.env.user.company_id.id,
                                        'plan_id': 1,
                                        'current_odometer': 0.0,
                                        'duration': 1,
                                        'duration_unit': 'day',
                                        'invoice_policies': 'advanced',
                                        'lock_state': 'open',
                                        'name': vehicle.vin_sn,
                                        'ref': vehicle.vin_sn,
                                        'vehicle_id': vehicle.id,
                                        'product_tmpl_id': product_id.product_tmpl_id.id,
                                        'sale_order_id': False, 'tenant_id': False, 'manager_id': False,
                                        'rent': False, 'duration': 0, 'state': 'close', 'rental_terms': 'short_term',
                                        'duration_unit': 'day', 'vehicle_lot_id': lot.id, 'product_id': product_id.id}

                                msg1 = ("This is my debug message analytic_account_data! %s", data)
                                _logger.error(msg1)

                                analytic_account = analytic_object.create(data)
                                msg1 = ("This is my debug message analytic_account! %s", analytic_account)
                                _logger.error(msg1)
                            if vehicle and analytic_account:
                                asset_data = {'name': vehicle.vin_sn, 'is_fleet': True, 'fleet_vehicle_id': vehicle.id,
                                              'category_id': default_asset_category_id, 'date': datetime.today(),
                                              'value': vehicle.vehicle_cost_price,
                                              'analytic_account_id': analytic_account.id,
                                              'asset_cost': vehicle.vehicle_cost_price,
                                              'partner_id': self.partner_id.id,
                                              'purch_id': purch_id.id}

                                msg1 = "This is my debug asset_data!"
                                _logger.error(msg1)
                                asset = asset_object.create(asset_data)
                                vehicle.update({
                                    'analytic_account_id': analytic_account.id,
                                    'asset_id': asset.id,
                                    'state_id': 7})
        return True
