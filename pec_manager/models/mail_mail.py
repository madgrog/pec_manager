import logging

from odoo import fields, models, tools

_logger = logging.getLogger(__name__)

class MailMail(models.Model):

    _inherit = 'mail.mail'

    is_pec = fields.Boolean('Is PEC?', default=False,
                            help='If set, the mail is sent to partner.pec_mail instead of partner.email.')

    def _send_prepare_values(self, partner=None):
        if self.model == "helpdesk.ticket":
            self.is_pec: bool = self.env['helpdesk.ticket'].search([('id', '=', self.res_id)]).pec_manager
        if not self.is_pec:
            return super(MailMail, self)._send_prepare_values(partner=partner)
        else:
            self.ensure_one()
            body = self._send_prepare_body()
            body_alternative = tools.html2plaintext(body)
            """ select PEC email address as recipient if exists, else select normal email """
            selected_mail = partner.pec_mail if partner.pec_mail else partner.email
            if partner:
                emails_normalized = tools.email_normalize_all(selected_mail)
                if emails_normalized:
                    email_to = [
                        tools.formataddr((partner.name or 'False', selected_mail or 'False'))
                        for email in emails_normalized
                    ]
                else:
                    email_to = tools.email_split_and_format(self.email_to)
            else:
                email_to = tools.email_split_and_format(self.email_to)
            """ === """
            res = {
                'body': body,
                'body_alternative': body_alternative,
                'email_to': email_to,
            }
            return res
