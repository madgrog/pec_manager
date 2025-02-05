from odoo import fields, models


class FetchmailServer(models.Model):
    """Incoming POP/IMAP mail server account"""

    _inherit = 'fetchmail.server'
    is_pec = fields.Boolean("Is PEC?", default=False)
