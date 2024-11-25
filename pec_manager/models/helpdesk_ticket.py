import logging

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    pec_manager = fields.Boolean("Enable PEC management?", default=False)
    original_team_id = fields.Many2one('helpdesk.team', string='Original Team id', index=True)

    @api.depends('partner_id.pec_mail')
    def _compute_partner_email(self):
        _logger.info("_compute_partner_email: %s", self)
        for ticket in self:
            if not ticket.pec_manager:
                return super(HelpdeskTicket, self)._compute_partner_email()
            else:   
                if ticket.partner_id:
                    ticket.partner_email = ticket.partner_id.pec_mail

    def _inverse_partner_email(self):
        for ticket in self:
            if not ticket.pec_manager:
                return super(HelpdeskTicket, self)._inverse_partner_email()
            if ticket._get_partner_email_update():
                ticket.partner_id.pec_mail = ticket.partner_email

    @api.onchange('pec_manager')
    def _toggle_partner_email(self):
        # Switch ticket partner email between pec and standard email
        self._compute_partner_email()

    @api.model_create_multi
    def create(self, list_value):
        list_value[0]["original_team_id"] = list_value[0]["team_id"]
        return super(HelpdeskTicket, self).create(list_value)
    
    def _get_partner_email_update(self):
        self.ensure_one()
        if not self.pec_manager:
            return super(HelpdeskTicket, self)._get_partner_email_update()
        else:
            if self.partner_id and self.partner_email != self.partner_id.pec_mail:
                ticket_email_normalized = tools.email_normalize(self.partner_email) or self.partner_email or False
                partner_email_normalized = tools.email_normalize(self.partner_id.pec_mail) or self.partner_id.pec_mail or False
                return ticket_email_normalized != partner_email_normalized
            return False
