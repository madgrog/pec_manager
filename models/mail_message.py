from odoo import models, fields


class Message(models.Model):
    _inherit = 'mail.message'

    pec_type = fields.Selection([
        ('posta-certificata', 'Pec Mail'),
        ('accettazione', 'Acceptance'),
        ('non-accettazione', 'No Acceptance'),
        ('presa-in-carico', 'In Progress'),
        ('avvenuta-consegna', 'Delivery'),
        ('errore-consegna', 'Delivery Error'),
        ('preavviso-errore-consegna', 'Notice Delivery Error'),
        ('rilevazione-virus', 'Virus Detected')],
        'PEC Type', readonly=True,
        help="",)
    pec_msg_id = fields.Char(
        'PEC-Message-Id',
        help='Message unique identifier', readonly=True)
