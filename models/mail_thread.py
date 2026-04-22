import email
import email.policy
import logging

from odoo import _, api, models, tools
from odoo.tools.mail import email_split

import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def is_server_pec(self):
        if 'default_fetchmail_server_id' in self._context:
            srv_id = self._context.get('default_fetchmail_server_id')
            return self.env['fetchmail.server'].search([('id', '=', srv_id)]).is_pec
        return False

    def parse_daticert(self, daticert):
        msg_dict = {}
        root = ET.fromstring(daticert)
        message = None
        if 'tipo' in root.attrib:
            msg_dict['pec_type'] = root.attrib['tipo']
        # if 'errore' in root.attrib:
        #     msg_dict['err_type'] = root.attrib['errore']
        for child in root:
            if child.tag == 'intestazione':
                for child2 in child:
                    if child2.tag == 'mittente':
                        msg_dict['email_from'] = child2.text
            if child.tag == 'dati':
                for child2 in child:
                    if child2.tag == 'msgid':
                        msg_dict['message_id'] = child2.text
                    if child2.tag == 'identificativo':
                        msg_dict['pec_msg_id'] = child2.text
                    if child2.tag == 'consegna':
                        recipient_id = self._FindPartnersPec(
                            message, child2.text)
                        if recipient_id:
                            msg_dict['recipient_id'] = recipient_id
                        msg_dict['recipient_addr'] = child2.text
        return msg_dict

    def _get_msg_anomalia(self, msg):
        to = None
        msg_id = None
        parser = email.Parser.HeaderParser()
        msg_val = email.message_from_string(
            parser.parsestr(msg.as_string()).get_payload()
        )
        if 'To' in msg_val:
            to = msg_val['To']
        if 'X-Riferimento-Message-ID'in msg_val:
            msg_id = msg_val['X-Riferimento-Message-ID']
        return to, msg_id

    def _get_msg_delivery(self, msg):
        for dsn in msg.get_payload():
            if 'Action' in dsn:
                return dsn['Action']

    def _get_msg_payload(self, msg, parts=None, num=0):
        """
            This method recursively checks the message structure and
                saves the informations (bodies, attachments,
                pkcs7 signatures, etc.) in a dictionary.

            The method parameters are:

             - msg is the multipart message to process; the first time
             the method is called it is exactly the Original.eml message,
             that is: the email as it arrives from the imap server.
             The method is called recursively when a multipart structure is
             found, in this case msg is a multipart inside the Original.eml
             message and the num param is the depth of the multipart inside
             the Original.eml message.
             - parts is the dictionary where the informations are saved
             - num is an integer that refers to the depth
                of the msg content in the Original.eml message

            Some examples of the structure for the different kind of pec messages
            can be found in the docs folder of this module
        """
        if parts is None:
            parts = {}
        for part in msg.get_payload():
            filename = part.get_param('filename', None, 'content-disposition')
            if not filename:
                filename = part.get_param('name', None)
            if filename:
                if isinstance(filename, tuple):
                    # RFC2231
                    filename = email.utils.collapse_rfc2231_value(
                        filename).strip()
                # else:
                #     filename = decode(filename)
            # Returns the files for a normal pec email
            if num == 0 and part.get_content_type() == \
                    'application/x-pkcs7-signature' and \
                    filename == 'smime.p7s':
                parts['smime.p7s'] = part.get_payload(decode=True)
            elif num == 1 and part.get_content_type() == \
                    'application/xml' and \
                    filename == 'daticert.xml':
                parts['daticert.xml'] = part.get_payload(decode=True)
            elif num == 1 and part.get_content_type() == \
                    'message/rfc822' and \
                    filename == 'postacert.eml':
                parts['postacert.eml'] = part.get_payload()[0]
            # If something went wrong: get basic info of the original message
            elif part.get_content_type() == \
                    'multipart/report':
                parts['report'] = True
            elif part.get_content_type() == \
                    'message/delivery-status':
                parts['delivery-status'] = self._get_msg_delivery(part)
            # If rfc822-headers is found get original msg info from payload
            elif part.get_content_type() == \
                    'text/rfc822-headers':
                parts['To'], parts['Msg_ID'] = \
                    self._get_msg_anomalia(part)
            # If no rfc822-headers than get info from original daticert.xml
            elif 'report' in parts and 'Msg_ID' not in parts and \
                    'daticert.xml' not in parts and \
                    part.get_content_type() == \
                    'application/xml' and \
                    filename == 'daticert.xml':
                origin_daticert = part.get_payload(decode=True)
                # parsed_daticert = self.parse_daticert(cr, uid, origin_daticert)
                parsed_daticert = self.parse_daticert(origin_daticert)
                if 'recipient_addr' in parsed_daticert:
                    parts['To'] = parsed_daticert['recipient_addr']
                if 'msgid' in parsed_daticert:
                    parts['Msg_ID'] = parsed_daticert['msgid']
            else:
                pass
            # At last, if msg is multipart then call this method iteratively
            if part.is_multipart():
                parts = self._get_msg_payload(part,
                                              parts=parts, num=num + 1)
        return parts

    def _message_extract_payload_receipt(self, message,
                                         save_original=False):
        """
            Extract body as HTML and attachments from the mail message
        """
        attachments = []
        body = u''
        if save_original:
            attachments.append(('original_email.eml', message.as_string()))
        if not message.is_multipart() or \
                'text/' in message.get('content-type', ''):
            encoding = message.get_content_charset()
            body = message.get_payload(decode=True)
            body = tools.ustr(body, encoding, errors='replace')
            if message.get_content_type() == 'text/plain':
                # text/plain -> <pre/>
                body = tools.append_content_to_html(u'', body, preserve=True)
        else:
            alternative = False
            for part in message.walk():
                if part.get_content_type() == 'multipart/alternative':
                    alternative = True
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container
                filename = part.get_param('filename',
                                          None,
                                          'content-disposition')
                if not filename:
                    filename = part.get_param('name', None)
                if filename:
                    if isinstance(filename, tuple):
                        # RFC2231
                        filename = email.utils.collapse_rfc2231_value(
                            filename).strip()
                    # else:
                    #     filename = filename.decode()
                encoding = part.get_content_charset()  # None if attachment
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition', '')\
                        .strip().startswith('attachment'):
                    attachments.append((filename or 'attachment',
                                        part.get_payload(decode=True))
                                       )
                    continue
                # 2) text/plain -> <pre/>
                if part.get_content_type() == 'text/plain' and \
                        (not alternative or not body):
                    body = tools.append_content_to_html(
                        body,
                        tools.ustr(part.get_payload(decode=True),
                                   encoding, errors='replace'),
                        preserve=True)
                # 3) text/html -> raw
                elif part.get_content_type() == 'text/html':
                    continue
                # 4) Anything else -> attachment
                else:
                    attachments.append((filename or 'attachment',
                                        part.get_payload(decode=True))
                                       )
        return body, attachments

    @api.model
    def message_parse(self, message, save_original=False):
        """
            Override standard message_parse() to handle PEC email
        """

        # if email is not fetched from a PEC incoming server, parse with standard method
        if not self.is_server_pec():
            msg_dict = super(MailThread, self).message_parse(message, save_original)
            return msg_dict

        else:
            _logger.info("=== Parse message as PEC ====")
            daticert_dict = {}
            parts = {}
            num = 0
            parts = self._get_msg_payload(message, parts=parts, num=num)
            daticert = 'daticert.xml' in parts and parts['daticert.xml'] or None
            postacert = 'postacert.eml' in parts and parts['postacert.eml'] or None

            if daticert:
                daticert_dict = self.parse_daticert(daticert)
            else:
                if 'To' not in parts and 'Msg_ID' not in parts:
                    raise ValueError(_('PEC message does not contain daticert.xml'))
                else:
                    daticert_dict['recipient_addr'] = parts['To']
                    daticert_dict['message_id'] = parts['Msg_ID']
                    daticert_dict['pec_type'] = 'errore-consegna'
                    daticert_dict['pec_msg_id'] = message['Message-ID']
                    # daticert_dict['err_type'] = 'no-dest'
                    daticert_dict['email_from'] = message['From']

        if daticert_dict.get('pec_type') == 'posta-certificata':
            _logger.info("=== It's a PEC ====")
            if not postacert:
                raise ValueError(_('PEC message does not contain postacert.eml'))
            pec_msg_dict = super(MailThread, self).message_parse(postacert, save_original=False)
            pec_msg_dict['is_internal'] = False
            parent_ids = False
            ###
            if pec_msg_dict['in_reply_to']:
                _logger.info("in_reply_to: %s", pec_msg_dict['in_reply_to'])
                parent_ids = self.env['mail.message'].search(
                    [('pec_msg_id', '=', pec_msg_dict['in_reply_to'][1:-1])],
                    order='create_date DESC, id DESC',
                    limit=1)
                _logger.info("parent_ids: %s", parent_ids)
                _logger.info("==========")
            if pec_msg_dict['references'] and not parent_ids:
                _logger.info("references: %s", pec_msg_dict['references'])
                references_pec_msg_id_list = tools.mail_header_msgid_re.findall(pec_msg_dict['references'])
                parent_ids = self.env['mail.message'].search(
                    [('pec_msg_id', 'in', [x.strip() for x in references_pec_msg_id_list][1:-1])],
                    order='create_date DESC, id DESC',
                    limit=1)
                _logger.info("parent_ids: %s", parent_ids)
            if parent_ids:
                pec_msg_dict['parent_id'] = parent_ids.parent_id.id
                _logger.info("parent_id: %s", pec_msg_dict['parent_id'])
                pec_msg_dict['is_internal'] = parent_ids.subtype_id and parent_ids.subtype_id.internal or False
            ###
            # pec_msg_dict['attachments'] += [
            #     ('original_email.eml', message.as_string())]
        else:
            pec_msg_dict = super(MailThread, self).message_parse(
                message, save_original=False)
            envelope_message_id = pec_msg_dict["message_id"]
            if daticert_dict.get('pec_type') in ('avvenuta-consegna', 'errore-consegna', 'accettazione'):
                pec_msg_dict['body'], attachs = self._message_extract_payload_receipt(message, save_original=False)
                pec_msg_dict['references'] = daticert_dict['message_id']
                pec_msg_dict['attachments'].clear()
        pec_msg_dict['attachments'] += [
            ('original_email.eml', message.as_string())]
        pec_msg_dict.update(daticert_dict)

        # pec_msg_ids = []
        if (daticert_dict.get('message_id') and (daticert_dict.get('pec_type') != 'posta-certificata')):
            pec_msg_ids = self.env['mail.message'].search([('message_id', '=', daticert_dict['message_id'])])
            _logger.info("Start guessing thread for PEC notifications ====>")
            _logger.info("mgs_ids: %s", pec_msg_ids)
            _logger.info("==========")

            if len(pec_msg_ids) > 1:
                raise ValueError(_('Too many existing mails with message_id %s'), daticert_dict['message_id'])
            if pec_msg_ids:
                # I'm going to set this message as notification of the original
                # message and set the message_id of this message as the 
                # envelope message_id.
                pec_msg_dict['parent_id'] = pec_msg_ids[0].id
                _logger.info("parent_id: %s", pec_msg_dict['parent_id'])
                _logger.info("==========")
                pec_msg_dict['message_id'] = envelope_message_id
        # if message transport resend original mail with
        # transport error, marks in original message with
        # error, and after the server not save the original message
        # because is duplicate
        ## CHECK THIS CODE (I have no error pec emails to test)
        if (
            daticert_dict.get('message_id') and
            message['X-Trasporto'] == 'errore'
        ):
            pec_msg_ids = self.env['mail.message'].search([('message_id', '=', daticert_dict['message_id'])])
            if len(pec_msg_ids) > 1:
                raise ValueError(_('Too many existing mails with message_id %s'), daticert_dict['message_id'])
            else:
                self.env['mail.message'].write(pec_msg_ids, {pec_msg_ids, {'error': True }})

        return pec_msg_dict

    def _message_parse_extract_payload(self, message, message_dict, save_original=False):
        """
            Trying to fix some PDF attachments received with wrong Content-Type (*/*)
        """
        for part in message.walk():
            if part.get_content_type() == '*/*' and part.get_filename().endswith('.pdf'):
                part.replace_header('Content-Type', 'application/pdf')
        return super(MailThread, self)._message_parse_extract_payload(message, message_dict, save_original=save_original)

    def _FindPartnersPec(self, message=None, email_from=False):
        """
            create new method to search partner because
            the data of from field of messages is not found
            with _message_find_partners
        """
        res = False
        if email_from:
            partner_obj = self.env['res.partner'].search([('email', '=', email_from.strip())])
            if partner_obj:
                res = partner_obj[0]
        return res

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        """
            Filter ticket followers when sending PEC messages: do not send them to internal users.
            This avoids receiving back useless "accettazione" and "consegna" notifications.
        """
        recipients_data = super(MailThread, self)._notify_get_recipients(message, msg_vals, **kwargs)

        if self.env.context.get('fetchmail_cron_running') or self.env.context.get('active_model') != 'helpdesk.ticket':
            return recipients_data
        elif not self.pec_manager:
            return recipients_data
        else:
            filtered_recipients_data = []
            for recipient in recipients_data:
                partner = self.env['res.partner'].browse(recipient.get("id"))
                if partner.user_ids:
                    continue
                filtered_recipients_data.append(recipient)
            return filtered_recipients_data

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """
            Remove "button access" from PEC replies.
        """
        groups = super(MailThread, self)._notify_get_recipients_groups(message, model_description, msg_vals)
        if msg_vals['model'] == 'helpdesk.ticket' and self.pec_manager:
            portal_group = next(group for group in groups if group[0] == 'portal_customer')
            portal_group[2]['active'] = True
            portal_group[2]['has_button_access'] = False
        return groups

    def _get_message_create_valid_field_names(self):
        result = super(MailThread, self)._get_message_create_valid_field_names()
        result.update({'pec_type','pec_msg_id'})
        return result

    def _message_post_after_hook(self, message, msg_vals):
        """
            Change subtype to note if message is a PEC delivery notification avoiding message looping
            between Odoo and PEC service.
            Furthermore, swap message_id and pec_msg_id to permit correct routing of notification messages.
        """
        if (msg_vals.get("pec_type") and
                msg_vals.get("pec_type") != "posta-certificata" and
                msg_vals.get("message_type") == "email"):
            # edit subtype
            changed_subtype = self.env.ref("mail.mt_note")
            message.write({"subtype_id": changed_subtype.id})
            msg_vals['subtype_id'] = changed_subtype.id
            # swap message_id and pec_msg_id
            changed_message_id = "<" + msg_vals['pec_msg_id'] + ">"
            changed_pec_msg_id = msg_vals['message_id'][1:-1]
            message.write({"message_id": changed_message_id})
            msg_vals['message_id'] = changed_message_id
            message.write({"pec_msg_id": changed_pec_msg_id})
            msg_vals['pec_msg_id'] = changed_pec_msg_id

        return super(MailThread, self)._message_post_after_hook(message, msg_vals)

    def _message_route_process(self, message, message_dict, routes):
        # get sender e-mail address and forward in context for further processing
        # (Distinguish sender and recipients creating contacts)
        sender_emails = email_split(message_dict.get('email_from', ''))

        ctx = dict(self.env.context)

        if sender_emails:
            ctx['custom_mail_sender'] = sender_emails[0].lower()

        return super(MailThread, self.with_context(ctx))._message_route_process(
            message, message_dict, routes
        )