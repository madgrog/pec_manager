from odoo import fields, models, _

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
