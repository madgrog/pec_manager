import logging
import ast
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import remove_accents

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

    _sql_constraints = [
        ('alias_unique', 'UNIQUE(alias_name, alias_domain)', 'Unfortunately this email alias is already used, please choose a unique one')
    ]

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
            if bool(alias_defaults) or alias_defaults["pec_manager"] == True:
                alias_defaults.pop("pec_manager")
        else:
            alias_defaults = ast.literal_eval(self.alias_defaults)
            alias_defaults["pec_manager"] = True
        self.alias_defaults = str(alias_defaults)

    def _clean_and_check_unique(self, names):
        """When an alias name appears to already be an email, we keep the local
        part only. A sanitizing / cleaning is also performed on the name. If
        name already exists an UserError is raised. """

        _logger.info("Cleaning and checking unique alias names (catchall/bounces only)")

        def _sanitize_alias_name(name):
            """ Cleans and sanitizes the alias name """
            sanitized_name = remove_accents(name).lower().split('@')[0]
            sanitized_name = re.sub(r'[^\w+.]+', '-', sanitized_name)
            sanitized_name = re.sub(r'^\.+|\.+$|\.+(?=\.)', '', sanitized_name)
            sanitized_name = sanitized_name.encode('ascii', errors='replace').decode()
            return sanitized_name

        sanitized_names = [_sanitize_alias_name(name) for name in names]

        catchall_alias = self.env['ir.config_parameter'].sudo().get_param('mail.catchall.alias')
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param('mail.bounce.alias')
        alias_domain = self.alias_domain

        # matches catchall or bounce alias
        for sanitized_name in sanitized_names:
            if sanitized_name in [catchall_alias, bounce_alias]:
                matching_alias_name = '%s@%s' % (sanitized_name, alias_domain) if alias_domain else sanitized_name
                raise UserError(
                    _('The e-mail alias %(matching_alias_name)s is already used as %(alias_duplicate)s alias. Please choose another alias.',
                      matching_alias_name=matching_alias_name,
                      alias_duplicate=_('catchall') if sanitized_name == catchall_alias else _('bounce'))
                )

        # # matches existing alias
        # domain = [('alias_name', 'in', sanitized_names)]
        # if self:
        #     domain += [('id', 'not in', self.ids)]
        # matching_alias = self.search(domain, limit=1)
        # if not matching_alias:
        #     return sanitized_names
        #
        # sanitized_alias_name = _sanitize_alias_name(matching_alias.alias_name)
        # matching_alias_name = '%s@%s' % (sanitized_alias_name, alias_domain) if alias_domain else sanitized_alias_name
        # if matching_alias.alias_parent_model_id and matching_alias.alias_parent_thread_id:
        #     # If parent model and parent thread ID both are set, display document name also in the warning
        #     document_name = self.env[matching_alias.alias_parent_model_id.model].sudo().browse(matching_alias.alias_parent_thread_id).display_name
        #     raise UserError(
        #         _('The e-mail alias %(matching_alias_name)s is already used by the %(document_name)s %(model_name)s. Choose another alias or change it on the other document.',
        #           matching_alias_name=matching_alias_name,
        #           document_name=document_name,
        #           model_name=matching_alias.alias_parent_model_id.name)
        #         )
        # raise UserError(
        #     _('The e-mail alias %(matching_alias_name)s is already linked with %(alias_model_name)s. Choose another alias or change it on the linked model.',
        #       matching_alias_name=matching_alias_name,
        #       alias_model_name=matching_alias.alias_model_id.name)
        # )
        return sanitized_names
