from odoo import fields, models

class AliasDomain(models.Model):
    _inherit = "mail.alias.domain"

    is_pec = fields.Boolean("Is PEC?", default=False)
