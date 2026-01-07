from odoo import models, api


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    @api.model_create_multi
    def create(self, vals_list):
        filtered_vals_list = []
        for vals in vals_list:
            partner = self.env['res.partner'].browse(vals.get("res_partner_id"))
            if partner.user_ids:
                continue
            filtered_vals_list.append(vals)

        return super(MailNotification, self).create(filtered_vals_list)