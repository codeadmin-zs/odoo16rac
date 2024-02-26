from odoo import models, fields, tools, api
from psycopg2 import sql


class FleetRentalVehicleReport(models.Model):
    _inherit = "report.fleet.rental"

    product_id = fields.Many2one('product.template', string='Vehicle Categories')
    total_rent = fields.Float(string='Total Rent')
    cost = fields.Float(string="Rent Revenue")
    v_brand = fields.Many2one('fleet.vehicle.model.brand', string="Model")
    state = fields.Selection([('draft', 'Booked'), ('hand_over', 'Hand Over'), ('open', 'In Progress'),
                              ('return', 'Return'), ('pending', 'To Renew'), ('close', 'Closed'),
                              ('cancelled', 'Cancelled')], string="State")
    amount_type = fields.Selection(string='Amount Type', selection=[
        ('total_rent', 'Total Rent'),
        ('paid_amount', 'Paid Amount')
    ], readonly=True)
    rental_terms = fields.Selection(
        [('short_term', 'Short Term'),
         ('long_term', 'Long Term'), ('spot', 'Spot Rental'),
         ('online', 'Online Booking')],
        string='Rental Terms')

    # def _select(self):
    #     select_str = """
    #          SELECT
    #                 (select 1 ) AS nbr,
    #                 t.id as id,
    #                 t.name as name,
    #                 t.vehicle_brand as v_brand,
    #                 t.vehicle_id as vehicle_id,
    #                 t.tenant_id as customer_id,
    #                 t.date_start as rent_start_date,
    #                 t.date as rent_end_date,
    #                 t.state as state,
    #                 t.total_rent as cost,
    #                 t.product_tmpl_id as product_id,
    #                 t.rental_terms as rental_terms
    #     """
    #     return select_str
    #
    # def _group_by(self):
    #     group_by_str = """
    #             GROUP BY
    #                 t.id,
    #                 name,
    #                 v_brand,
    #                 customer_id,
    #                 vehicle_id,
    #                 cost,
    #                 rent_start_date,
    #                 rent_end_date,
    #                 state,
    #                 product_id,
    #                 rental_terms
    #     """
    #     return group_by_str
    #
    # def init(self):
    #     tools.sql.drop_view_if_exists(self._cr, 'report_fleet_rental')
    #     self._cr.execute("""
    #         CREATE view report_fleet_rental as
    #           %s
    #           FROM account_analytic_account t
    #           WHERE t.rent
    #            > 0.0
    #             %s
    #     """ %  (self._select(), self._group_by()))

    def init(self):
        cr = self.env.cr
        # , CASE
        # t.total_rent / t.duration
        # WHEN
        # t.duration_unit = ' )
        qry1 = """
                    CREATE VIEW %s AS ()
                    """
        total_rent = """SELECT
                    t.id as id,
                    t.name as name,
                    t.vehicle_brand as v_brand,
                    t.vehicle_id as vehicle_id,
                    t.tenant_id as customer_id,
                    t.date_start as rent_start_date,
                    t.date as rent_end_date,
                    t.state as state, 
                    (CASE WHEN t.duration_unit = 'month' THEN COALESCE(sum(t.rent/t.duration), 0) 
                          ELSE COALESCE(sum(t.rent), 0) END) as cost ,
                    t.product_tmpl_id as product_id,
                    t.rental_terms as rental_terms,
                    'total_rent' AS amount_type
        FROM account_analytic_account t
              WHERE t.rent
               > 0.0
        GROUP BY
                    t.id,
                    name,
                    v_brand,
                    customer_id,
                    vehicle_id,
                    rent_start_date,
                    rent_end_date,
                    state,
                    product_id,
                    rental_terms"""

        paid_amount = """SELECT
                    t.id as id,
                    t.name as name,
                    t.vehicle_brand as v_brand,
                    t.vehicle_id as vehicle_id,
                    t.tenant_id as customer_id,
                    t.date_start as rent_start_date,
                    t.date as rent_end_date,
                    t.state as state,
                    COALESCE(sum(am.amount_untaxed), 0) AS cost,
                    t.product_tmpl_id as product_id,
                    t.rental_terms as rental_terms,
                    'paid_amount' AS amount_type
                FROM account_analytic_account t
                JOIN tenancy_rent_schedule trs ON trs.tenancy_id = t.id
                JOIN account_move am ON trs.invc_id = am.id
                WHERE am.amount_untaxed > 0.00 AND am.state = 'posted' 
                GROUP BY
                    t.id,
                    t.name,
                    v_brand,
                    customer_id,
                    t.vehicle_id,
                    rent_start_date,
                    rent_end_date,
                    t.state,
                    product_id,
                    rental_terms"""

        query = """
    WITH total_rent AS (%s),
    paid_amount AS (%s)
    SELECT
        vehicle_id AS id,
        vehicle_id,
        name,
        v_brand,
        customer_id,
        product_id,
        rent_start_date,
        rent_end_date,
        state,
        rental_terms,
        cost,
        'total_rent' AS amount_type
    FROM
        total_rent tr
    UNION ALL (
        SELECT
            vehicle_id AS id,
            vehicle_id,
            name,
            v_brand,
            customer_id,
            product_id,
            rent_start_date,
            rent_end_date,
            state,
            rental_terms,
            cost,
            'paid_amount' AS amount_type
            FROM
                paid_amount cc)
    """ % (total_rent, paid_amount)
        tools.drop_view_if_exists(self.env.cr, self._table)
        qry1 = sql.SQL("""CREATE or REPLACE VIEW {} as ({})""").format(
                sql.Identifier(self._table),
                sql.SQL(query)
            )
        self.env.cr.execute(qry1
            )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(FleetRentalVehicleReport, self).fields_get(allfields, attributes=attributes)
        unwanted = ['car_color', 'cost_frequency', 'total', 'tools_missing_cost', 'damage_cost', 'damage_cost_sub', 'total_cost', 'total_rent', 'car_brand', 'rental_type']
        for each in unwanted:
            del res[each]
        return res
