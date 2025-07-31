from odoo import fields, models


class FetchmailServer(models.Model):
    """
        Specify if fetch mail server is a PEC service.
    """

    _inherit = 'fetchmail.server'
    is_pec = fields.Boolean("Is PEC?", default=False)
