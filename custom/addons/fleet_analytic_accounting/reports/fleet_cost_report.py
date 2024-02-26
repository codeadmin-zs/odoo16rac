from psycopg2 import sql

from odoo import tools
from odoo import models, fields, api


class FleetCostReport(models.Model):
    _inherit = "fleet.vehicle.cost.report"

    product_id = fields.Many2one('product.template', string='Vehicle Categories')
    customer_id = fields.Many2one('res.partner', string='Customer')
    fuel_type = fields.Many2one('fleet.category.vehicle.fuel', string='Fuel')
    cost_type = fields.Selection(string='Cost Type', selection=[
        ('depreciation', 'Depreciation'),
        ('service', 'Service')
    ], readonly=True)

    def init(self):
        cr = self.env.cr
        service = """SELECT
            ve.id AS vehicle_id,
            ve.company_id AS company_id,
            ve.name AS name,
            ve.vehicle_prodcut_template_id AS product_id,
            ve.driver_id AS driver_id,
            ve.fuel_type AS fuel_type,
            date(date_trunc('month', d)) AS date_start,
            COALESCE(sum(se.amount), 0) AS
            cost,
            'service' AS cost_type
        FROM
            fleet_vehicle ve
        CROSS JOIN generate_series((
                SELECT
                    min(acquisition_date)
                    FROM fleet_vehicle), CURRENT_DATE, '1 month') d
        LEFT JOIN fleet_vehicle_log_services se ON se.vehicle_id = ve.id
            AND date_trunc('month', se.date) = date_trunc('month', d)
        WHERE
            ve.active AND se.active AND se.state != 'cancelled' AND se.service_type_id != 1
        GROUP BY
            ve.id,
            ve.company_id,
            ve.name,
            date_start,
            d
        ORDER BY
            ve.id,
            date_start"""

        depreciation = """SELECT
                    ve.id AS vehicle_id,
                    ve.company_id AS company_id,
                    ve.name AS name,
                    ve.vehicle_prodcut_template_id AS product_id,
                    ve.driver_id AS driver_id,
                    ve.fuel_type AS fuel_type,
                    date(date_trunc('month', d)) AS date_start,
                    COALESCE(sum(am.amount_total), 0) AS
                    cost,
                    'depreciation' AS cost_type
                FROM
                    fleet_vehicle ve
                CROSS JOIN generate_series((
                        SELECT
                            min(acquisition_date)
                            FROM fleet_vehicle), CURRENT_DATE, '1 month') d
                LEFT JOIN account_asset_asset ass ON ass.fleet_vehicle_id = ve.id
                JOIN account_move am ON am.loan_id = ass.id
                    AND date_trunc('month', am.date) = date_trunc('month', d)
                WHERE
                    ve.active AND am.state = 'posted'
                GROUP BY
                    ve.id,
                    ve.company_id,
                    ve.name,
                    date_start,
                    d
                ORDER BY
                    ve.id,
                    date_start"""

        # cost = """SELECT
        #             ve.id AS vehicle_id,
        #             ve.company_id AS company_id,
        #             ve.name AS name,
        #             ve.vehicle_prodcut_template_id AS product_id,
        #             ve.driver_id AS driver_id,
        #             ve.fuel_type AS fuel_type,
        #             date(date_trunc('month', d)) AS date_start,
        #             COALESCE(sum(cod.total_rent), 0) AS
        #             cost,
        #             'service' AS cost_type
        #         FROM
        #             fleet_vehicle ve
        #         CROSS JOIN generate_series((
        #             SELECT
        #                 min(acquisition_date)
        #                 FROM fleet_vehicle), CURRENT_DATE, '1 month') d
        #                 LEFT JOIN account_analytic_account cod ON cod.vehicle_id = ve.id
        #                     AND date_trunc('month', cod.date_start) <= date_trunc('month', d)
        #                     AND date_trunc('month', cod.date) >= date_trunc('month', d)
        #         WHERE
        #             ve.active AND cod.total_rent > 0
        #         GROUP BY
        #             ve.id,
        #             ve.company_id,
        #             ve.name,
        #             date_start,
        #             d
        #         ORDER BY
        #             ve.id,
        #             date_start"""

        query = """
    WITH service_costs AS (%s),
    depreciation_costs AS (%s)
    SELECT
        vehicle_id AS id,
        company_id,
        vehicle_id,
        name,
        product_id,
        driver_id,
        fuel_type,
        date_start,
        cost,
        'service' as cost_type
    FROM
        service_costs sc
    UNION ALL (
        SELECT
            vehicle_id AS id,
            company_id,
            vehicle_id,
            name,
            product_id,
            driver_id,
            fuel_type,
            date_start,
            cost,
            'depreciation' as cost_type
        FROM
            depreciation_costs cc)
    """ % (service, depreciation)
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            sql.SQL("""CREATE or REPLACE VIEW {} as ({})""").format(
                sql.Identifier(self._table),
                sql.SQL(query)
            ))

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(FleetCostReport, self).fields_get(allfields, attributes=attributes)
        unwanted = ['customer_id']
        for each in unwanted:
            del res[each]
        return res