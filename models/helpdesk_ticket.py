import logging

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    pec_manager = fields.Boolean("Enable PEC management?", default=False)
    # original_team_id field can be removed
    original_team_id = fields.Many2one('helpdesk.team', string='Original Team id', index=True)

    # Can be deleted, now useless.
    @api.model_create_multi
    def create(self, list_value):
        list_value[0]["original_team_id"] = list_value[0]["team_id"]
        return super(HelpdeskTicket, self).create(list_value)

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'team_id' in init_values:
            return self.env.ref('pec_manager.mt_ticket_team')
        return super(HelpdeskTicket, self)._track_subtype(init_values)
