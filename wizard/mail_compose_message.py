from odoo import models

import ast


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _prepare_mail_values(self, res_ids):
        """
            Workaround for mail.compose.message._prepare_mail_values
            When user replies to a PEC ticket using specified template, "reply_to" value is "lost" in mail preparation
            somewhere. While looking for it, force it injecting in this function.
        """
        res = super(MailComposer, self)._prepare_mail_values(res_ids)
        if self.model != "helpdesk.ticket":
            return res
        else:
            res_ids_list = ast.literal_eval(self.res_ids)
            for res_id in res_ids_list:
                is_pec: bool = self.env[self.model].sudo().search(
                    [('id', '=', res_id)]).pec_manager
                if is_pec:
                    res[res_id]["reply_to"] = self.reply_to
            return res

    # @api.model
    # def default_get(self, fields):
    #     """
    #         If the ticket you are working on is managed as PEC, open the reply wizard
    #         preloaded with the custom template.
    #         This permits sending replies with the correct sender and "reply-to" value.
    #     """
    #     result = super(MailComposer, self).default_get(fields)
    #     # if "model" in res and res['model'] == "helpdesk.ticket":
    #     #     load_pec_template: bool = self.env[res["model"]].sudo().search(
    #     #         [('id', '=', res["res_ids"][1])]).pec_manager
    #     #     if load_pec_template:
    #     #         res['template_id'] = self.env['mail.template'].with_context(lang='en_US').search(
    #     #         [('name', 'like', 'Helpdesk: Reply as PEC')], limit=1)
    #     if result.get('model') == "helpdesk.ticket":
    #         ticket = self.env["helpdesk.ticket"].browse(eval(result.get('res_ids')))
    #
    #         if ticket.original_team_id.alias_domain_id.is_pec:
    #             template = self.env.ref("pec_manager.ticket_reply_as_pec_email_template")
    #         else:
    #             template = False
    #
    #         if template:
    #             result["template_id"] = template.id
    #
    #             template_values = template.generate_email(ticket.id)
    #             result.update({
    #                 "subject": template_values.get("subject"),
    #                 "body": template_values.get("body"),
    #                 "email_from": template_values.get("email_from"),
    #             })
    #
    #     return result

    # def action_send_mail(self):
    #     res = super(MailComposer, self).action_send_mail()

        # hardcode is_pec to True (will fix later)
        # is_pec = True

        # for composer in self:
        #     if composer.model == "helpdesk.ticket":
        #         message = self.env['mail.message'].search([
        #             ('model', '=', composer.model),
        #             ('res_id', '=', eval(composer.res_ids)[0]),
        #         ], order='id desc', limit=1)
        #
        #         if message:
        #             # maybe useless
        #             message.subtype_id = self.env.ref("pec_manager.mt_external_messages_only").id
        #
        #             # remove internal users notifications
        #             notif_recs = self.env['mail.notification'].search([
        #                 ('mail_message_id', '=', message.id)
        #             ])
        #             internal_notifs = notif_recs.filtered(
        #                 lambda n: n.res_partner_id.user_ids
        #             )
        #             internal_notifs.unlink()

        # return res