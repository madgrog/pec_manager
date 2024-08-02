import logging

from odoo import fields, models, api
from odoo.tools import email_re

_logger = logging.getLogger(__name__)


class MailComposer(models.TransientModel):

    _inherit = 'mail.compose.message'

    is_pec = fields.Boolean('Is Pec?', help='If set, the reply wizard can send PEC messages instead of standard emails.')

    @api.model
    def default_get(self, fields):
        """
            If the ticket you are working on is managed as PEC, open the reply wizard
            preloaded with the custom template that permits to send replies with correct
            sender and PEC SMTP server (if recipient has a PEC email defined).
        """
        res = super(MailComposer, self).default_get(fields)
        res['is_pec']: bool = self.env[self._context.get("default_model")].sudo().search(
            [('id', '=', self._context.get("default_res_id"))]).pec_manager
        if res['is_pec']:
            res['template_id'] = self.env['mail.template'].search(
            [('name', 'like', 'Helpdesk: Reply as PEC')], limit=1)
        return res
