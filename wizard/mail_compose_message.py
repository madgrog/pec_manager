import logging

from odoo import fields, models, api
from odoo.tools import email_re

_logger = logging.getLogger(__name__)


class MailComposer(models.TransientModel):

    _inherit = 'mail.compose.message'

    # is_pec = fields.Boolean('Is Pec?', help='If set, the reply wizard can send PEC messages instead of standard emails.')

    def _prepare_mail_values(self, res_ids):
        """
            Workaround for mail.compose.message._prepare_mail_values
            When user replies to a PEC ticket using specified template, "reply_to" value is "lost" in mail preparation
            somewhere. While looking for it, force it injecting in this function.
        """
        res = super(MailComposer, self)._prepare_mail_values(res_ids)
        for key in res:
            res[key]["reply_to"] = self.reply_to
        return res

    @api.model
    def default_get(self, fields):
        """
            If the ticket you are working on is managed as PEC, open the reply wizard
            preloaded with the custom template that permits to send replies with correct
            sender and PEC SMTP server (if recipient has a PEC email defined).
        """
        res = super(MailComposer, self).default_get(fields)
        if "model" in res and res['model'] == "helpdesk.ticket":
            load_pec_template: bool = self.env[res["model"]].sudo().search(
                [('id', '=', res["res_ids"][1])]).pec_manager
            if load_pec_template:
                res['template_id'] = self.env['mail.template'].with_context(lang='en_US').search(
                [('name', 'like', 'Helpdesk: Reply as PEC')], limit=1)
        return res
