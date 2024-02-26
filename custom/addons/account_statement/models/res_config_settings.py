# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date,datetime,timedelta
from dateutil.relativedelta import relativedelta


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    
    
    @api.constrains ('statement_days')
    def _check_statement_days(self):
        if self.send_statement and self.period != 'weekly':
            if self.statement_days > 31 or self.statement_days <= 0:
                raise ValidationError(_('Enter Valid Statement Date Range'))
            
    
    
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update({
            'statement_days':int(self.env['ir.config_parameter'].sudo().get_param('account_statement.statement_days')) or None,     
            'weekly_days':self.env['ir.config_parameter'].sudo().get_param('account_statement.weekly_days') or None,       
            })
        return res


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param('account_statement.statement_days',self.statement_days or None)
        ICPSudo.set_param('account_statement.weekly_days',self.weekly_days or None)

        if self.send_statement and self.period != 'weekly':
            statement_cron = self.env['ir.model.data'].xmlid_to_object('account_statement.autometic_send_statement_cron')
            statement_cron.active = self.send_statement
            cron_datetime = self.change_cron_time(self.statement_days)
            statement_cron.nextcall = str(cron_datetime)
            
    def change_cron_time(self,days):
        now = datetime.now()
        
        current_month = now.month
        current_date = now.day
        current_year = now.year
        expected_date = datetime(now.year, now.month, days, now.hour, now.minute, now.second)
        
        cron_datetime = expected_date
        
        if current_date>days:
            cron_datetime = expected_date + relativedelta(months=+1)
        return cron_datetime
    
    
    send_statement = fields.Boolean(related='company_id.send_statement',string="Send Customer Statement",readonly=False)
    period = fields.Selection(string='Period',related='company_id.period',readonly=False)
    statement_days = fields.Integer(related='company_id.statement_days',string="Statement Date",readonly=False)

    weekly_days = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ],related='company_id.weekly_days',string="Weekly Send Day",readonly=False)

    
