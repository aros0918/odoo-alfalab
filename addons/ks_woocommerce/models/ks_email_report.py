# -*- coding: utf-8 -*-

import logging
import re
from datetime import date

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class KsEmailReport(models.Model):
    _name = 'ks.woo.email.report'
    _rec_name = 'ks_email_conf_id'
    _description = '''WooCommerce Mail Report Configuration'''

    ks_email_conf_id = fields.Char(string="Email Configuration Id", readonly=True, default=lambda self: 'New')
    ks_wc_instance_ids = fields.Many2many("ks.woo.connector.instance", string="WooCommerce Instance", required=True, help="Displays WooCommerce Name")
    email_ids = fields.Many2many("email.entry", string="Email IDs", readonly=True,
                                 compute='_fill_emails_based_on_instance', help="Displays list of email ID's")
    email_template = fields.Many2one("mail.template", string="Email Templates", readonly=True,
                                     compute='get_template', help=" Displays Email Template name")
    user_id = fields.Many2one("res.users", string="Users", readonly=True, default=lambda self: self.env.user)
    subjects = fields.Char(string="Email Subject", help="Display Subject of the Email")
    body = fields.Text(string="Email Body", help="Display Body of the Email")
    active = fields.Boolean(string="Status", readonly=True, default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            rec = super(KsEmailReport, self).create(vals)
            seq = self.env['ir.sequence'].next_by_code('increment_your_field') or ('New')
            rec.ks_email_conf_id = seq
        return rec

    @api.constrains('ks_wc_instance_ids', 'email_ids')
    def _check_email(self):
        if not self.email_ids:
            raise ValidationError("Email Fields cannot be empty")

    @api.onchange("ks_wc_instance_ids")
    @api.depends("ks_wc_instance_ids", "email_ids")
    def _fill_emails_based_on_instance(self):
        """
        inputs emails fields with instance wise emails
        :return:
        """
        if self:
            if self.ks_wc_instance_ids:
                domain = []
                for rec in self.ks_wc_instance_ids:
                    for email in rec.ks_email_ids:
                        domain.append((4, email.id, 0))
                self.email_ids = domain
            else:
                self.email_ids = False

    def get_template(self):
        """
        Finds the template to send email
        :return:
        """
        if self:
            self.email_template = self.env.ref('ks_woocommerce.ks_email_report_template').id
        else:
            self.email_template = False

    def get_emails(self):
        """
        Fetches the email ids
        :return:
        """
        emails = []
        for id in self.email_ids:
            emails.append(id.email)
        emails = set(emails)
        emails = ','.join(emails)
        return emails

    def get_instances(self):
        """
        fetches the instance
        :return:
        """
        instances = []
        for instance in self.ks_wc_instance_ids:
            instances.append(instance.ks_instance_name)
        instances = set(instances)
        instances = ', '.join(instances)
        return instances

    def get_today_date(self):
        return str(date.today())

    def cleanhtml(self, raw_html):
        """
        Parse raw html to text
        :param raw_html: html tags code
        :return: clean text
        """
        cleaner = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
        cleantext = re.sub(cleaner, '', raw_html)
        return cleantext

    def get_subject(self):
        """
        Finds the subjects of the email
        :return: subject
        """
        if self.subjects:
            subject = '%s [%s]' % (self.subjects, str(date.today()))
        else:
            subject = self.get_default_subject()
        return subject

    def get_body(self):
        """
                Finds the body of the email
                :return: body
                """
        if self.body:
            body = 'Instance Name:- [%s] \n %s' % (self.get_instances(), self.cleanhtml(self.body))
        else:
            body = self.get_default_body()
        return body

    def get_default_subject(self):
        """
        :return: default subject
        """
        return 'Woocommerce Daily Sales Report [%s]' % str(date.today())

    def get_default_body(self):
        """
        :return: default body
        """
        return '''
            Hello User, 
            You can find the daily sales report attached in the mail which has all the details
            regarding Instance, Sales etc.
            Thank You for using WooCommerce Connector
            Regards,
            WC Connector
        '''

    def get_order_count_per_instance(self, instance_id):
        """
        Counts orders
        :param instance_id: woo instance
        :return: counts of orders per instance
        """
        return self.env['sale.order'].search_count([('ks_wc_instance', '=', instance_id),  ('state', 'not in', ['cancel', 'draft'])])

    def get_total_orders(self):
        """
        Get total orders for an instance
        :return: count
        """
        count = 0
        for rec in self.ks_wc_instance_ids:
            count += self.env['sale.order'].search_count([('ks_wc_instance', '=', rec.id),  ('state', 'not in', ['cancel', 'draft'])])
        return count

    def get_order_lines(self, instance_id):
        """
        fetched order lines
        :param instance_id: woo instance
        :return: order lines
        """
        domain = [('state', 'not in', ['cancel', 'draft']),
                  ('ks_wc_instance', '=', instance_id)]
        return self.env['sale.order'].search(domain)

    def toggle_active(self):
        """
        smart button to active email conf record
        :return:
        """
        if not self.active:
            self.active = True

    def toggle_archive(self):
        if self.active:
            self.active = False

    def action_send_email(self):
        """
        Cron method to send email daily
        :return:
        """
        if not self:
            records = self.env['ks.woo.email.report'].search(
                [('active', '=', True), ('ks_wc_instance_ids.id', '!=', False), ('email_ids.id', '!=', False)])
            for rec in records:
                template_id = rec.env.ref('ks_woocommerce.ks_email_report_template').id
                template = rec.env['mail.template'].browse(template_id)
                template.send_mail(rec.id, force_send=True)
        else:
            for rec in self:
                if rec.active:
                    template_id = rec.env.ref('ks_woocommerce.ks_email_report_template').id
                    template = rec.env['mail.template'].browse(template_id)
                    template.send_mail(rec.id, force_send=True)
                else:
                    _logger.info("Record should be active. Inactive record id %s" % rec.ks_email_conf_id)


class KsEmail(models.Model):
    _name = 'email.entry'
    _rec_name = 'email'
    _description = "Email Entry"

    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", ondelete='cascade')
    email = fields.Char(string="Email")
