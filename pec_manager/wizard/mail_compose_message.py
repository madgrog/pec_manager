import logging

from odoo import fields, models, api
from odoo.tools import email_re

_logger = logging.getLogger(__name__)


class MailComposer(models.TransientModel):

    _inherit = 'mail.compose.message'

    is_pec = fields.Boolean('Is Pec?', help='If set, the mail is sent to partner.pec_mail instead of partner.email.')

    @api.model
    def default_get(self, fields):
        _logger.info("=== custom default_get() ===")
        res = super(MailComposer, self).default_get(fields)
        res['is_pec']: bool = self.env[self._context.get("default_model")].sudo().search(
            [('id', '=', self._context.get("default_res_id"))]).pec_manager
        if res['is_pec']:
            res['template_id'] = self.env['mail.template'].search(
            [('name', 'like', 'Helpdesk: Reply as PEC')], limit=1)
        return res

    def _action_send_mail(self, auto_commit=False):
        _logger.info('_action_send_mail: is PEC? %s', self.is_pec)
        return super(MailComposer, self)._action_send_mail()

    # def _process_recipient_values(self, mail_values_dict):
    #     # Preprocess res.partners to batch-fetch from db if recipient_ids is present
    #     # it means they are partners (the only object to fill get_default_recipient this way)
    #     _logger.info("=== _PROCESS_RECIPIENT_VALUES() ===")
    #     _logger.info(mail_values_dict)
    #     _logger.info("Is PEC? %s", self.is_pec)
    #
    #     if not self.is_pec:
    #         return super(MailComposer, self)._process_recipient_values(mail_values_dict)
    #     else:
    #         recipient_pids = [
    #             recipient_command[1]
    #             for mail_values in mail_values_dict.values()
    #             # recipient_ids is a list of x2m command tuples at this point
    #             for recipient_command in mail_values.get('recipient_ids') or []
    #             if recipient_command[1]
    #         ]
    #         recipient_emails = {
    #             p.id: p.pec_mail
    #             for p in self.env['res.partner'].browse(set(recipient_pids))
    #         } if recipient_pids else {}
    #         _logger.info("recipient_emails: %s", recipient_emails)
    #
    #         recipients_info = {}
    #         for record_id, mail_values in mail_values_dict.items():
    #             mail_to = []
    #             if mail_values.get('email_to'):
    #                 mail_to += email_re.findall(mail_values['email_to'])
    #                 # if unrecognized email in email_to -> keep it as used for further processing
    #                 if not mail_to:
    #                     mail_to.append(mail_values['email_to'])
    #             # add email from recipients (res.partner)
    #             mail_to += [
    #                 recipient_emails[recipient_command[1]]
    #                 for recipient_command in mail_values.get('recipient_ids') or []
    #                 if recipient_command[1]
    #             ]
    #             mail_to = list(set(mail_to))
    #             recipients_info[record_id] = {
    #                 'mail_to': mail_to,
    #                 'mail_to_normalized': [
    #                     tools.email_normalize(mail)
    #                     for mail in mail_to
    #                     if tools.email_normalize(mail)
    #                 ]
    #             }
    #         _logger.info(self)
    #         _logger.info("recipient_info: %s", recipients_info)
    #         _logger.info("===================================")
    #         return recipients_info
