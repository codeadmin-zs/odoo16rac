from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrderCountFlag(models.Model):
    _inherit = 'sale.order'

    rental_count_flag = fields.Boolean(string="Rental Count Flag")
    product_uom_qty_count = fields.Integer(string="Quantity Count")


class SrMultiProduct(models.TransientModel):
    _name = 'sr.multi.product'

    @api.onchange('product_id')
    def get_vehicle_domain(self):
        sale_order = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        order_lines = self.env['sale.order.line'].search([('order_id', '=', sale_order.id)])
        res = {}
        vehicle_list = []
        for each in order_lines:
            if each.product_id:
                fleet_vehicle = self.env['fleet.vehicle'].search([
                    ('vehicle_prodcut_id', '=', each.product_id.id),
                    ('state_id.name', '!=', 'Sold'), ('state_id.name', '=', 'Available')])
                if fleet_vehicle:
                    vehicle_list.extend(fleet_vehicle.ids)
        res['domain'] = {'vehicle_ids': [('id', 'in', vehicle_list)]}
        return res

    product_id = fields.Many2many('product.product', string='Product')
    vehicle_ids = fields.Many2many('fleet.vehicle', string="Vehicles")

    # @api.multi
    def add_rental_contract(self):
        sale_order = self.env[self._context['active_model']].browse(self._context.get('active_id', False))
        order_lines = self.env['sale.order.line'].search([('order_id', '=', sale_order.id)])
        self.env.context = dict(self.env.context)
        self.env.context.update({'default_rental_rank': 1, 'default_is_rental_order': True})
        del self.env.context['active_model']
        del self.env.context['active_id']
        del self.env.context['active_ids']
        for line in order_lines:
            wizard_data = line.rental_wizard_id
            vehicle = self.env['fleet.vehicle'].search(
                [('id', 'in', self.vehicle_ids.ids), ('vehicle_prodcut_id', '=', wizard_data.product_id.id)])
            if vehicle and sale_order.rental_term == 'long_term':
                sale_order_qty_count = sale_order.product_uom_qty_count + len(vehicle)
                sale_order.update({'product_uom_qty_count': sale_order_qty_count})
                if sale_order_qty_count == wizard_data.quantity:
                    sale_order.update({'rental_count_flag': True})
                elif sale_order_qty_count > wizard_data.quantity:
                    raise ValidationError("Quantity of the Rental Contract should be equal to the Quotation Quantity.")
                wizard_data.license_plate_no = vehicle.ids
                line.lot_state = 'lot_added'
            else:
                raise ValidationError('Please Select/Check the License Numbers.')
        sale_order.create_rental()
        return True
