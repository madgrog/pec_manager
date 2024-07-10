import logging
import ast
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

"""
    TO DO:
    - remove hard coded domains;
    - generate ALIAS_DOMAINS from:
        * mail.catchall.domain
        * some kind of user configurable secondary domains (PEC or not)
    - maybe a simple model to store (PEC) domains with configuration parameters.

"""

ALIAS_DOMAINS = [
    ('pec.it', 'pec.it'),
    ('legalmail.it', 'legalmail.it'),
]


class Alias(models.Model):
    _inherit = "mail.alias"

    def _get_catchall_domain(self):
        return self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")

    def _compute_alias_domains(self):
        catchall_domain = self._get_catchall_domain()
        catchall_domain_tuple = (catchall_domain, catchall_domain)
        alias_domains = ALIAS_DOMAINS[:]
        alias_domains.insert(0, catchall_domain_tuple)
        return alias_domains

    alias_domain = fields.Selection(_compute_alias_domains, string='Alias Domain', required=True,
                                    default=_get_catchall_domain, help="Select mail domain")

    @api.onchange('alias_domain')
    def _toggle_pec_manager(self):
        if self.alias_domain == self._get_catchall_domain():
            alias_defaults = ast.literal_eval(self.alias_defaults)
            alias_defaults.pop("pec_manager")
        else:
            alias_defaults = ast.literal_eval(self.alias_defaults)
            alias_defaults["pec_manager"] = True
        self.alias_defaults = str(alias_defaults)
