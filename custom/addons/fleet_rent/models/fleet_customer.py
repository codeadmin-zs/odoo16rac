from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class ResPartnerExtend(models.Model):
    _inherit = 'res.partner'

    # Adding additional fields in customers form
    tenant = fields.Boolean(string='Is Tenant?', default=True)
    passport_number = fields.Char(string="Passport")
    passport_issued_country = fields.Many2one('res.country', 'Passport Issued Country')
    passport_expiry_date = fields.Date(string='Passport Expiry Date')
    passport_doc = fields.Binary(string='Passport')
    passport_doc_name = fields.Char()
    dl_number = fields.Char(string="Driving License")
    date_of_issue_DL = fields.Date(string='DL Issue Date')
    date_of_expiry_DL = fields.Date(string='DL Expiry Date')
    date_of_birth = fields.Date(string='Date Of Birth')
    country_of_issue_DL = fields.Many2one('res.country', 'DL Issued Country')
    is_driver = fields.Boolean(string='Is Driver')
    dl_attachment = fields.Binary(string='Driving License')
    dl_attachment_name = fields.Char()
    id_attachment = fields.Binary(string='Identity Proof')
    id_attachment_name = fields.Char()
    d_id = fields.Char(string='ID-Card', size=64)
    insurance = fields.Boolean(string='Insurance')
    on_rental_contract = fields.Integer(string='On a Rental Contract', default=0)
    national_id = fields.Char(string='National id')

    @api.constrains('passport_expiry_date')
    def _check_date_field_passport_expiry_date(self):
        for record in self:
            if record.is_driver:
                if record.passport_expiry_date < fields.Date.context_today(self):
                    raise models.ValidationError("Passport Expired..,Add a Customer with Valid Passport.")

    @api.constrains('date_of_issue_DL')
    def _check_date_field_date_of_issue_dl(self):
        for record in self:
            if record.is_driver:
                if record.date_of_issue_DL > fields.Date.context_today(self):
                    raise models.ValidationError("Enter a Valid Driving Licence Issue Date.")

    @api.constrains('date_of_expiry_DL')
    def _check_date_field_date_of_expiry_dl(self):
        for record in self:
            if record.is_driver:
                if record.date_of_expiry_DL < fields.Date.context_today(self):
                    raise models.ValidationError("Driving Licence Expired....Enter a Valid Driving Licence..")

    @api.constrains('date_of_birth')
    def _check_date_date_of_birth(self):
        current_date = datetime.now().date()
        for record in self:
            if record.is_driver:
                age_delta = relativedelta(current_date, record.date_of_birth)
                age = age_delta.years
                if age < 18:
                    raise models.ValidationError("Driver is Under Aged")






