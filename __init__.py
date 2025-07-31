from . import models
from . import wizard

# from odoo import api, SUPERUSER_ID

def _restore_helpdesk(env):
    """
        This method restores original Enterprise Helpdesk
    """
    wid = env['ir.ui.menu'].search([('web_icon', '=', 'pec_manager,static/description/menu_icon.png')])
    for record in wid:
        record.write({'web_icon': 'helpdesk,static/description/icon.png'})
    print("Restored stock Helpdesk menu icon!")
