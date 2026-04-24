from odoo import fields, models, _, api
from odoo.modules import get_module_resource
import os, base64


class Partner(models.Model):
    _inherit = 'res.partner'

    type = fields.Selection(
        selection_add = [('pec', 'PEC Address')],
        help="- Contact: Use this to organize the contact details of employees of a given company (e.g. CEO, CFO, ...).\n"
             "- Invoice Address: Preferred address for all invoices. Selected by default when you invoice an order that belongs to this company.\n"
             "- Delivery Address: Preferred address for all deliveries. Selected by default when you deliver an order that belongs to this company.\n"
             "- Other: Other address for the company (e.g. subsidiary, ...).\n"
             "- PEC Address: Italian Certified E-mail Address."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
           When creating new partners processing PEC E-mails, create new sender partners as pec type contact
           with custom avatar and properly formatted firstname and lastname.
           Recipients processed as usual.
        """

        sender_email = self.env.context.get('custom_mail_sender')
        fetchmail_server_id = self.env.context.get('default_fetchmail_server_id')
        if sender_email and self.env['fetchmail.server'].search([('id', '=', fetchmail_server_id)]).is_pec:

            for vals in vals_list:
                current_email = (vals.get('email') or '').lower()
                if current_email == sender_email:
                    # Path to PEC avatar (now is module icon, could be other in the near future)
                    img_path = get_module_resource('pec_manager', 'static/description', 'icon.png')
                    default_image = False
                    if img_path:
                        with open(img_path, 'rb') as f:
                            default_image = base64.b64encode(f.read())
                    # Set PEC avatar only if it's not provided
                    if not vals.get('image_1920') and default_image:
                        vals['image_1920'] = default_image
                    res = super().create(vals_list)
                    res['firstname'] = 'PEC'
                    res['lastname'] = res['email_normalized']
                    # res['name'] = 'PEC '+res['email_normalized']
                    res['email_formatted'] = '"PEC '+res['email_normalized']+'" <'+res['email_normalized']+'>'
                    res['type'] = 'pec'
                    res['company_id'] = ''
                    return res

        return super().create(vals_list)