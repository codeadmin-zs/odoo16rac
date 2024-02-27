
from psycopg2 import sql

from odoo import tools
from odoo import fields, models


class FleetRentalVehicleReport(models.Model):
    _name = "report.fleet.vehicle.utilisation"

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    state = fields.Many2one('fleet.vehicle.state', string='State')

    def _select(self):
        select_str = """
             SELECT
                    fv.id as id,
                    fv.name as name,
                    fv.state as state
        """
        return select_str

    def _group_by(self):
        group_by_str = """
                GROUP BY
                    state
        """
        return group_by_str

    def init(self):
        tools.sql.drop_view_if_exists(self._cr, 'report_fleet_rental')
        self._cr.execute("""
            CREATE view report_fleet_vehicle as
              %s
              FROM fleet_vehicle fv
                %s
        """ % (self._select(), self._group_by()))