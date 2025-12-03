from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    pec_manager = fields.Boolean("Enable PEC management?", default=False)

    @api.model_create_multi
    def create(self, list_value):
        res = super(HelpdeskTicket, self).create(list_value)
        res.pec_manager = res.team_id.alias_domain_id.is_pec
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'team_id' in init_values:
            return self.env.ref('pec_manager.mt_ticket_team')
        return super(HelpdeskTicket, self)._track_subtype(init_values)
