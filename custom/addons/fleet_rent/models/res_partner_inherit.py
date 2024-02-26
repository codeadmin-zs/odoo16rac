from odoo import models, fields, api
import re
from datetime import datetime

class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'
# Email Validator
    @api.constrains('email')
    def _check_email_format(self):
        for partner in self:
            if partner.email and not self._validate_email(partner.email):
                raise models.ValidationError('Invalid email format.')

    @staticmethod
    def _validate_email(value):
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, value))
# Mobile Number Validator

    @api.constrains('mobile','phone')
    def _check_phone_number_format(self):
        for partner in self:
            if partner.mobile and not self._validate_mobile_no(partner.mobile):
                raise models.ValidationError('Invalid Mobile Number......')
            if partner.phone and not self._validate_mobile_no(partner.phone):
               raise models.ValidationError('Please enter a valid phone number.')

    @staticmethod
    def _validate_mobile_no(value):
        pattern = r'^\d{10,11}$'
        return bool(re.match(pattern, value))

#Phone Number Validator

    # @api.constrains('phone')
    # def _check_phone_number_format(self):
    #     for partner in self:
    #         if partner.phone and not self._validate_phone_no(partner.phone):
    #             raise models.ValidationError('Invalid Phone Number......')
    #
    # @staticmethod
    # def _validate_phone_no(value):
    #     pattern = r'^\d{10,11}$'
    #     return bool(re.match(pattern, value))


class PurchaseOrderInherit(models.Model):
    _inherit = "purchase.order"
    @api.constrains('date_order')
    def _check_date(self):
        if self.date_order.date() < datetime.today().date():
            raise models.ValidationError('Order date date must be on/after today.')

    @api.constrains('date_planned')
    def _check_date(self):
        if self.date_order.date() > self.date_planned.date():
            raise models.ValidationError('Delivery date date must be on/after the order date.')