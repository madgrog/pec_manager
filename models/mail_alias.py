# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import _, api, fields, models


class Alias(models.Model):
    _inherit = "mail.alias"

    @api.onchange('alias_domain_id')
    def _toggle_pec_manager(self):
        if self.alias_domain_id.is_pec:
            alias_defaults = ast.literal_eval(self.alias_defaults)
            alias_defaults["pec_manager"] = True
        else:
            alias_defaults = ast.literal_eval(self.alias_defaults)
            if "pec_manager" in alias_defaults and alias_defaults["pec_manager"] == True:
                alias_defaults.pop("pec_manager")
        self.alias_defaults = str(alias_defaults)