import logging

from odoo import fields, models, tools

_logger = logging.getLogger(__name__)


class MailMail(models.Model):

    _inherit = 'mail.mail'

    is_pec = fields.Boolean('Is Pec?', help='If set, the mail is sent to partner.pec_mail instead of partner.email.')

    def _send_prepare_values(self, partner=None):
        _logger.info("==== CUSTOM _SEND_PREPARE_DATA() ====")
        if not self.is_pec:
            _logger.info("==== _SEND_PREPARE_VALUE() NOT PEC ====")
            _logger.info("self: %s", self)
            res = super(MailMail, self)._send_prepare_values(partner=partner)
            _logger.info("res: %s", res)
            return res
        else:
            _logger.info("==== _SEND_PREPARE_VALUE() PEC ====")
            _logger.info("self: %s", self)
            self.ensure_one()
            body = self._send_prepare_body()
            body_alternative = tools.html2plaintext(body)
            if partner:
                email_to = [tools.formataddr((partner.name or 'False', partner.pec_mail or 'False'))]
                _logger.info("email_to: %s", email_to)
            else:
                email_to = tools.email_split_and_format(self.email_to)
                _logger.info("email_to: %s", email_to)
            res = {
                'body': body,
                'body_alternative': body_alternative,
                'email_to': email_to,
            }
            return res
