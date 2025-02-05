from . import models
from . import wizard
# from odoo import api, SUPERUSER_ID

# def _restore_helpdesk(cr, registry):
#     """
#         This method restores original Enterprise Helpdesk
#         App icon and two record rules customized to support
#         group based access to Helpdesk Teams and Tickets.
#     """
#     env = api.Environment(cr, SUPERUSER_ID, {})
#     wid = env['ir.ui.menu'].search([('web_icon', '=', 'pec_manager,static/description/menu_icon.png')])
#     for record in wid:
#         record.write({'web_icon': 'helpdesk,static/description/icon.svg'})
#     cr.execute("""UPDATE ir_rule SET domain_force = '[''|'',
#                                             (''privacy_visibility'', ''!='', ''invited_internal''),
#                                             (''message_partner_ids'', ''in'', [user.partner_id.id])
#                                         ]'
#                     WHERE name = 'Helpdesk User'""")
#     cr.execute("""UPDATE ir_rule SET domain_force = '[''|'',
#                                         ''|'',
#                                             (''team_id.privacy_visibility'', ''!='', ''invited_internal''),
#                                             (''team_id.message_partner_ids'', ''in'', [user.partner_id.id]),
#                                             (''message_partner_ids'', ''in'', [user.partner_id.id]),
#                                         ]'
#                     WHERE name = 'Helpdesk Ticket User'""")
#     print("PEC Manager module uninstalled!")
