# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date,datetime,timedelta
from dateutil.relativedelta import relativedelta


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None):
        res = super(MailTemplate, self).send_mail(res_id, force_send=False, raise_exception=False, email_values=None)

        mail = self.env['mail.mail'].browse(res)

        if self._context.get('monthly_attachments'):
            attachment_ids = []
            for attachment in self._context.get('monthly_attachments'):
                attachment_data = {
                    'name': attachment[0],
                    'datas': attachment[1],
                    'type': 'binary',
                    'res_model': 'mail.message',
                    'res_id': mail.mail_message_id.id,
                }
                attach = self.env['ir.attachment'].create(attachment_data)
                attachment_ids.append(attach.id)
            self.env['mail.mail'].sudo().browse(res).attachment_ids = [(6, 0, attachment_ids)]
            
        if self._context.get('weekly_attachments'):
            attachment_ids = []
            for attachment in self._context.get('weekly_attachments'):
                attachment_data = {
                    'name': attachment[0],
                    'datas': attachment[1],
                    'type': 'binary',
                    'res_model': 'mail.message',
                    'res_id': mail.mail_message_id.id,
                }
                attach = self.env['ir.attachment'].create(attachment_data)
                attachment_ids.append(attach.id)
            self.env['mail.mail'].sudo().browse(res).attachment_ids = [(6, 0, attachment_ids)]
        return res
    
           
