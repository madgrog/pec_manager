import ast
import email
import email.policy
import logging
import re

from email.message import EmailMessage

from odoo import _, api, models, tools

import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def is_server_pec(self):
        if 'default_fetchmail_server_id' in self._context:
            srv_id = self._context.get('default_fetchmail_server_id')
            return self.env['fetchmail.server'].search([('id', '=', srv_id)]).is_pec
        return False

    """
    def force_create_partner(self, context=None):
        #if context is None:
        #    context = {}
        #server_pool = self.pool.get('fetchmail.server')
        #if 'fetchmail_server_id' in context:
        #    srv_id = context.get('fetchmail_server_id')
        #    server = server_pool.browse(cr,
        #                                SUPERUSER_ID,
        #                                srv_id,
        #                                context=context)
        #    if server:
        #        return server.force_create_partner_from_mail
        return False
    """

    def parse_daticert(self, daticert):
        msg_dict = {}
        root = ET.fromstring(daticert)
        message = None
        if 'tipo' in root.attrib:
            msg_dict['pec_type'] = root.attrib['tipo']
        if 'errore' in root.attrib:
            msg_dict['err_type'] = root.attrib['errore']
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
                            # message, child2.text, context=context)
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
        """Extract body as HTML and attachments from the mail message"""
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
            return super(MailThread, self).message_parse(message, save_original)

        # msg_dict = {}
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
                daticert_dict['err_type'] = 'no-dest'
                daticert_dict['email_from'] = message['From']

        ## Log parsed daticert.xml
        #_logger.info("= daticert_dict =")
        #for k in daticert_dict:
        #    _logger.info(k + ": " + daticert_dict[k])
        #_logger.info("=================")
        # =======================
        
        if daticert_dict.get('pec_type') == 'posta-certificata':
            _logger.info("=== It's a PEC ====")
            if not postacert:
                raise ValueError(_('PEC message does not contain postacert.eml'))
            msg_dict = super(MailThread, self).message_parse(
                postacert, save_original=False)
            parent_ids = False
            ###
            if msg_dict['in_reply_to']:
                _logger.info("in_reply_to: %s", msg_dict['in_reply_to'])
                parent_ids = self.env['mail.message'].search(
                    [('pec_msg_id', '=', msg_dict['in_reply_to'][1:-1])],
                    order='create_date DESC, id DESC',
                    limit=1)
                _logger.info("parent_ids: %s", parent_ids)
                _logger.info("==========")
            if msg_dict['references'] and not parent_ids:
                _logger.info("references: %s", msg_dict['references'])
                references_msg_id_list = tools.mail_header_msgid_re.findall(msg_dict['references'])
                parent_ids = self.env['mail.message'].search(
                    [('pec_msg_id', 'in', [x.strip() for x in references_msg_id_list][1:-1])],
                    order='create_date DESC, id DESC',
                    limit=1)
                _logger.info("parent_ids: %s", parent_ids)
            if parent_ids:
                msg_dict['parent_id'] = parent_ids.parent_id.id
                _logger.info("parent_id: %s", msg_dict['parent_id'])
                msg_dict['is_internal'] = parent_ids.subtype_id and parent_ids.subtype_id.internal or False
            ###
            msg_dict['attachments'] += [
                ('original_email.eml', message.as_string())]
        else:
            msg_dict = super(MailThread, self).message_parse(
                message, save_original=False)
            envelope_message_id = msg_dict["message_id"]
            if daticert_dict.get('pec_type') in ('avvenuta-consegna', 'errore-consegna', 'accettazione'):
                msg_dict['body'], attachs = self._message_extract_payload_receipt(message, save_original=False)
                msg_dict['references'] = daticert_dict['message_id']
        msg_dict.update(daticert_dict)

        ## Log parsed message
        #_logger.info("=== msg_dict ====")
        #for k in msg_dict:
        #    if k == "body":
        #        _logger.info("body: ...")
        #    elif k == "attachments":
        #        _logger.info("attachments: ...")
        #    elif not msg_dict[k]:
        #        _logger.info(k + ": _empty_")
        #    elif isinstance(msg_dict[k], (list, bool)):
        #        _logger.info("%s: %s", k, str(msg_dict[k]))
        #    else:
        #        _logger.info("%s: %s", k, msg_dict[k])
        #        _logger.info("=================")
        ## =======================

        # msg_ids = []
        if (daticert_dict.get('message_id') and (daticert_dict.get('pec_type') != 'posta-certificata')):
            msg_ids = self.env['mail.message'].search([('message_id', '=', daticert_dict['message_id'])])
            _logger.info("Start guessing thread for PEC notifications ====>")
            _logger.info("mgs_ids: %s", msg_ids)
            _logger.info("==========")

            if len(msg_ids) > 1:
                raise ValueError(_('Too many existing mails with message_id %s'), daticert_dict['message_id'])
            if msg_ids:
                # I'm going to set this message as notification of the original
                # message and set the message_id of this message as the 
                # envelope message_id.
                msg_dict['parent_id'] = msg_ids[0].id
                _logger.info("parent_id: %s", msg_dict['parent_id'])
                _logger.info("==========")
                msg_dict['message_id'] = envelope_message_id
        # if message transport resend original mail with
        # transport error, marks in original message with
        # error, and after the server not save the original message
        # because is duplicate
        ## CHECK THIS CODE (I have no error pec emails to test)
        if (
            daticert_dict.get('message_id') and
            message['X-Trasporto'] == 'errore'
        ):
            msg_ids = self.env['mail.message'].search([('message_id', '=', daticert_dict['message_id'])])
            if len(msg_ids) > 1:
                raise ValueError(_('Too many existing mails with message_id %s'), daticert_dict['message_id'])
            else:
                self.env['mail.message'].write(msg_ids, {msg_ids, {'error': True }})
        ###
        ###
        author_id = self._FindOrCreatePartnersPec(
            message, daticert_dict.get('email_from'))
        if author_id:
            msg_dict['author_id'] = author_id.id
            _logger.info("author_id: %s", author_id.id)
        msg_dict['server_id'] = self._context.get('default_fetchmail_server_id')

        _logger.info("======== PARSED MESSAGE ==============")
        _logger.info('message_id: %s', msg_dict['message_id'])
        _logger.info("======================================")

        return msg_dict

    def _FindPartnersPec(self, message=None, email_from=False):
        """
        create new method to search partner because
        the data of from field of messages is not found
        with _message_find_partners
        """
        res = False
        if email_from:
            partner_obj = self.env['res.partner'].search([('pec_mail', '=', email_from.strip())])
            if partner_obj:
                res = partner_obj[0]
        return res

    def _FindOrCreatePartnersPec(self, message=None, pec_address=False):
        """
        Search for a partner and if not found create it [only if allowed].
        """
        res = self._FindPartnersPec(message, pec_address)
        # if not res and self.force_create_partner():
        if not res:
            res = self.env['res.partner'].create(
                {
                    'name': pec_address,
                    'email': '',
                    'pec_mail': pec_address,
                    'is_company': True
                })
        return res

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        if message.message_type == 'email' and (not message.pec_type == 'posta-certificata'):
            # _logger.info("=================================")
            # _logger.info("= message_type = %s", message.message_type)
            # _logger.info("= pec_type = %s", message.pec_type)
            # _logger.info("= DO NOT NOTIFY OR SEND EMAIL")
            # _logger.info("=================================")
            return False
        else:
            # _logger.info("=================================")
            # _logger.info("= message_type = %s", message.message_type)
            # _logger.info("= pec_type = %s", message.pec_type)
            # _logger.info("= NOTIFY OR SEND EMAIL!")
            # _logger.info("=================================")
            return super(MailThread, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """ Attempt to figure out the correct target model, thread_id,
        custom_values and user_id to use for an incoming message.
        Multiple values may be returned, if a message had multiple
        recipients matching existing mail.aliases, for example.

        The following heuristics are used, in this order:

         * if the message replies to an existing thread by having a Message-Id
           that matches an existing mail_message.message_id, we take the original
           message model/thread_id pair and ignore custom_value as no creation will
           take place;
         * look for a mail.alias entry matching the message recipients and use the
           corresponding model, thread_id, custom_values and user_id. This could
           lead to a thread update or creation depending on the alias;
         * fallback on provided ``model``, ``thread_id`` and ``custom_values``;
         * raise an exception as no route has been found

        :param string message: an email.message instance
        :param dict message_dict: dictionary holding parsed message variables
        :param string model: the fallback model to use if the message does not match
            any of the currently configured mail aliases (may be None if a matching
            alias is supposed to be present)
        :type dict custom_values: optional dictionary of default field values
            to pass to ``message_new`` if a new record needs to be created.
            Ignored if the thread record already exists, and also if a matching
            mail.alias was found (aliases define their own defaults)
        :param int thread_id: optional ID of the record/thread from ``model`` to
            which this mail should be attached. Only used if the message does not
            reply to an existing thread and does not match any mail alias.
        :return: list of routes [(model, thread_id, custom_values, user_id, alias)]

        :raises: ValueError, TypeError
        """

        # if email is not fetched from a PEC incoming server, route with standard method
        if not self.is_server_pec():
            return super(MailThread, self).message_route(message, message_dict, model=model, thread_id=thread_id, custom_values=custom_values)

        _logger.info("=========================")
        _logger.info("we are in custom message_route")
        _logger.info("=========================")

        if not isinstance(message, EmailMessage):
            raise TypeError('message must be an email.message.EmailMessage at this point')
        catchall_alias = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param("mail.bounce.alias")
        fallback_model = model

        # get email.message.Message variables for future processing
        message_id = message_dict['message_id']

        # compute references to find if message is a reply to an existing thread
        _logger.info("=========================")
        _logger.info("pec_type: %s", message_dict['pec_type'])
        _logger.info("references: %s", message_dict['references'])
        _logger.info("in_reply_to: %s", message_dict['in_reply_to'])
        _logger.info("=========================")
        if message_dict['pec_type'] == 'posta-certificata':
            thread_references = message_dict['references'][1:-1] or message_dict['in_reply_to'][1:-1]
        else:
            thread_references = message_dict['references'] or message_dict['in_reply_to']
        _logger.info("thread_references: %s", thread_references)
        _logger.info("=========================")
        msg_references = [
            re.sub(r'[\r\n\t ]+', r'', ref)  # "Unfold" buggy references
            for ref in tools.mail_header_msgid_re.findall(thread_references)
            if 'reply_to' not in ref
        ]
        _logger.info("msg_references: %s", msg_references)
        _logger.info("=========================")
        if message_dict['pec_type'] == 'posta-certificata':
            mail_messages = self.env['mail.message'].sudo().search([('pec_msg_id', '=', thread_references)], limit=1, order='id desc, pec_msg_id')
        else:
            mail_messages = self.env['mail.message'].sudo().search([('message_id', '=', thread_references)], limit=1, order='id desc, message_id')
        is_a_reply = bool(mail_messages)
        reply_model, reply_thread_id = mail_messages.model, mail_messages.res_id

        # author and recipients
        email_from = message_dict['email_from']
        email_from_localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        email_to = message_dict['to']
        email_to_localparts = [
            e.split('@', 1)[0].lower()
            for e in (tools.email_split(email_to) or [''])
        ]
        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos_localparts = [
            e.split('@')[0].lower()
            for e in tools.email_split(message_dict['recipients'])
        ]
        rcpt_tos_valid_localparts = [to for to in rcpt_tos_localparts]

        # 0. Handle bounce: verify whether this is a bounced email and use it to collect bounce data
        #                   and update notifications for customers
        #    Bounce alias: if any To contains bounce_alias@domain
        #    Bounce message (not alias)
        #       See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #        As all MTA does not respect this RFC (googlemail is one of them),
        #       we also need to verify if the message come from "mailer-daemon"
        #    If not a bounce: reset bounce information
        if bounce_alias and any(email == bounce_alias for email in email_to_localparts):
            self._routing_handle_bounce(message, message_dict)
            return []
        if message.get_content_type() == 'multipart/report' or email_from_localpart == 'mailer-daemon':
            self._routing_handle_bounce(message, message_dict)
            return []
        self._routing_reset_bounce(message, message_dict)

        # 1. Handle reply
        #    if destination = alias with different model -> consider it is a forward and not a reply
        #    if destination = alias with same model -> check contact settings as they still apply
        if reply_model and reply_thread_id:
            reply_model_id = self.env['ir.model']._get_id(reply_model)
            other_model_aliases = self.env['mail.alias'].search([
                '&', '&',
                ('alias_name', '!=', False),
                ('alias_name', 'in', email_to_localparts),
                ('alias_model_id', '!=', reply_model_id),
            ])
            if other_model_aliases:
                is_a_reply = False
                rcpt_tos_valid_localparts = [to for to in rcpt_tos_valid_localparts if to in other_model_aliases.mapped('alias_name')]

        if is_a_reply:
            reply_model_id = self.env['ir.model']._get_id(reply_model)
            dest_aliases = self.env['mail.alias'].search([
                ('alias_name', 'in', rcpt_tos_localparts),
                ('alias_model_id', '=', reply_model_id)
            ], limit=1)

            user_id = self._mail_find_user_for_gateway(email_from, alias=dest_aliases).id or self._uid
            route = self._routing_check_route(
                message, message_dict,
                (reply_model, reply_thread_id, custom_values, user_id, dest_aliases),
                raise_exception=False)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, reply_model, reply_thread_id, custom_values, self._uid)
                return [route]
            elif route is False:
                return []

        # 2. Handle new incoming email by checking aliases and applying their settings
        if rcpt_tos_localparts:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)

            # check it does not directly contact catchall
            if catchall_alias and email_to_localparts and all(email_localpart == catchall_alias for email_localpart in email_to_localparts):
                _logger.info('Routing mail from %s to %s with Message-Id %s: direct write to catchall, bounce', email_from, email_to, message_id)
                body = self.env['ir.qweb']._render('mail.mail_bounce_catchall', {
                    'message': message,
                })
                self._routing_create_bounce_email(email_from, body, message, references=message_id, reply_to=self.env.company.email)
                return []

            dest_aliases = self.env['mail.alias'].search([('alias_name', 'in', rcpt_tos_valid_localparts)])
            if dest_aliases:
                routes = []
                for alias in dest_aliases:
                    user_id = self._mail_find_user_for_gateway(email_from, alias=alias).id or self._uid
                    route = (alias.sudo().alias_model_id.model, alias.alias_force_thread_id, ast.literal_eval(alias.alias_defaults), user_id, alias)
                    route = self._routing_check_route(message, message_dict, route, raise_exception=True)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, email_to, message_id, route)
                        routes.append(route)
                return routes

        # 3. Fallback to the provided parameters, if they work
        if fallback_model:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)
            user_id = self._mail_find_user_for_gateway(email_from).id or self._uid
            route = self._routing_check_route(
                message, message_dict,
                (fallback_model, thread_id, custom_values, user_id, None),
                raise_exception=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                    email_from, email_to, message_id, fallback_model, thread_id, custom_values, user_id)
                return [route]

        # ValueError if no routes found and if no bounce occurred
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, email_to, message_id)
        )

    @api.model
    def _mail_find_partner_from_emails(self, emails, records=None, force_create=False, extra_domain=False):

        _logger.info("=== _MAIL_FIND_PARTNER_INFO_FROM_EMAILS() ===")
        _logger.info(self._name)

        if (self._name != "helpdesk.ticket") or (self._name == "helpdesk.ticket" and not self.pec_manager):
            _logger.info("NON E' PEC")
            _logger.info("==========================================")
            return super(MailThread, self)._mail_find_partner_from_emails(emails, records=records, force_create=force_create, extra_domain=extra_domain)
        else:
            _logger.info("PEC!!!")
            _logger.info("==========================================")
            if records and issubclass(type(records), self.pool['mail.thread']):
                followers = records.mapped('message_partner_ids')
            else:
                followers = self.env['res.partner']
            catchall_domain = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.domain")

            # first, build a normalized email list and remove those linked to aliases to avoid adding aliases as partners
            normalized_emails = [tools.email_normalize(contact) for contact in emails if tools.email_normalize(contact)]
            if catchall_domain:
                domain_left_parts = [email.split('@')[0] for email in normalized_emails if email and email.split('@')[1] == catchall_domain.lower()]
                if domain_left_parts:
                    found_alias_names = self.env['mail.alias'].sudo().search([('alias_name', 'in', domain_left_parts)]).mapped('alias_name')
                    normalized_emails = [email for email in normalized_emails if email.split('@')[0] not in found_alias_names]

            done_partners = [follower for follower in followers if follower.pec_mail in normalized_emails]
            remaining = [email for email in normalized_emails if email not in [partner.pec_mail for partner in done_partners]]

            user_partners = self._mail_search_on_user(remaining, extra_domain=extra_domain)
            done_partners += [user_partner for user_partner in user_partners]
            remaining = [email for email in normalized_emails if email not in [partner.pec_mail for partner in done_partners]]

            partners = self._mail_search_on_partner(remaining, extra_domain=extra_domain)
            done_partners += [partner for partner in partners]
            remaining = [email for email in normalized_emails if email not in [partner.pec_mail for partner in done_partners]]

            # iterate and keep ordering
            partners = []
            for contact in emails:
                normalized_email = tools.email_normalize(contact)
                partner = next((partner for partner in done_partners if partner.pec_mail == normalized_email), self.env['res.partner'])
                if not partner and force_create and normalized_email in normalized_emails:
                    partner = self.env['res.partner'].browse(self.env['res.partner'].name_create(contact)[0])
                partners.append(partner)
            return partners
