# -*- coding: utf-8 -*-

import base64

from odoo import api, models, fields
from odoo.exceptions import ValidationError
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)


class KsWooWebhooksConfiguration(models.Model):
    _name = 'ks.webhooks.configuration'
    _description = 'WebHook Configuration'
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    operations = fields.Selection([('order_create', 'Order Create'),
                                   ('order_update', 'Order Update'),
                                   ('product_create', 'Product Create'),
                                   ('product_update', 'Product Update'),
                                   ('customer_create', 'Customer Create'),
                                   ('customer_update', 'Customer Update'),
                                   ('coupon_create', 'Coupon Create'),
                                   ('coupon_update', 'Coupon Update')],
                                  string="Operation", required=True, default=False)

    status = fields.Selection([('active', 'Active'),
                               ('paused', 'Paused'),
                               ('disabled', 'Disabled')], string="Hook Status", default='disabled',
                              readonly=True)

    base_url = fields.Char(string="Webhook Url", readonly=True, compute='_ks_compute_base_url')

    ks_instance_id = fields.Many2one("ks.woo.connector.instance", string="Woo Instance", readonly=True)
    ks_woo_id = fields.Char(string="WooCommerce Id", readonly=True)

    @api.depends('operations')
    def _ks_compute_base_url(self):
        """
        Computes URL for controllers webhook to request data
        :return:
        """
        for rec in self:
            if rec.ks_instance_id.ks_instance_state in ['active', 'connected']:
                ks_base = rec.env['ir.config_parameter'].sudo().get_param('web.base.url')
                ks_base_updated = ks_base.split("//")
                if len(ks_base_updated) > 1:
                    ks_base = 'https://' + ks_base_updated[1]
                if rec.operations:
                    selection_list = rec.operations.split('_')
                    rec.base_url = '%s/woo_hook/%s/%s/%s/%s/%s' % (ks_base,
                                                                   base64.urlsafe_b64encode(
                                                                       self.env.cr.dbname.encode("utf-8")).decode(
                                                                       "utf-8"),
                                                                str(self.env.user.id),
                                                                   rec.ks_instance_id.id,
                                                                   selection_list[0],
                                                                   selection_list[1])
                else:
                    rec.base_url = ''
            else:
                rec.base_url = ''
                _logger.info("Instance should be Active or Connected")

    def prepare_to_update_on_woo(self, odoo_data):
        """
        Prepares data to be updated on woocommerce
        :param odoo_data: json data
        :return:
        """
        data = {
            'name': odoo_data.get('name') or self.name,
            'status': odoo_data.get('status') or self.status,
            'topic': ".".join(odoo_data.get('operations').split("_")) + 'd' \
                if odoo_data.get('operations') else ".".join(self.operations.split("_")) + 'd',
            'delivery_url': odoo_data.get('base_url') or self.base_url
        }
        return data

    def write(self, vals):
        """
        Updates data on both webhook and odoo
        :param vals: creation data
        :return: rec
        """
        rec = super(KsWooWebhooksConfiguration, self).write(vals)
        '''data in vals will be used for updation
            self will have woo_id for which we want to update webhook
        '''
        instance_id = self.ks_instance_id
        if not instance_id:
            return rec
        webhook_id = self.ks_woo_id if self.ks_woo_id else vals.get('ks_woo_id')
        if self.ks_woo_id or vals.get('ks_woo_id'):
            data = self.prepare_to_update_on_woo(vals)
            ks_response_data = self.ks_update_webhook(instance_id, webhook_id, data)
        else:
            data = {
                'name': self.name,
                'status': self.status,
                'topic': ".".join(self.operations.split("_")) + 'd' if self.operations else ".",
                'delivery_url': self.base_url
            }
            response_data = self.ks_create_webhook(self.ks_instance_id, data)
            if response_data:
                rec.update({'ks_woo_id': response_data.get("id")})
            else:
                raise ValidationError("Fatal Error! While Syncing Webhook through Woo")
        return rec

    def params_update(self):
        """
        Toggle button update the status
        :return:
        """
        for rec in self:
            status = ['active', 'paused', 'disabled']
            index = status.index(rec.status)
            if index < len(status) - 1:
                value = status[index + 1]
                rec.write({'status': value})
            elif index == len(status) - 1:
                value = status[0]
                rec.write({'status': value})

    def params_sync(self):
        """
        Syncs parameter of webhook and create on woocommerce
        :return: None
        """
        data = self.ks_woocommerce_webhook_data(self.operations, self.base_url)
        response_data = self.ks_create_webhook(self.ks_instance_id, data)
        if response_data:
            self.update({
                'ks_woo_id': response_data.get('id'),
                'status': 'active'
            })
        else:
            _logger.error("Create webhook failed, No response found.")

    def ks_woocommerce_webhook_data(self, name, base_url):
        """
        Create a dictionary data which is posted on the woocommerce
        :param name: Name of the Webhook
        :param base_url: Base URL of the webhook
        :return: dictionary
        """
        return {
            'name': " ".join(name.split("_")).title(),
            'status': 'active',
            'topic': ".".join(name.split("_")) + 'd',
            'delivery_url': base_url
        }

    def ks_get_all_webhooks(self, wc_instance):
        """
        retrieve all the details of webhooks for that particular instance
        :param instance_id: Id of instance for whose webhooks has to be retrived
        :return: list of dictionaries for all webhooks
        """
        multi_api_call = True
        per_page = 100
        page = 1
        ks_all_webhooks = []
        try:
            wcapi = wc_instance.ks_woo_api_authentication()
            while multi_api_call:
                webhooks_response = wcapi.get("webhooks", params={'per_page': per_page, 'page': page})
                if webhooks_response.status_code in [200, 201]:
                    ks_all_webhooks.extend(webhooks_response.json())
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="webhook",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=wc_instance,
                                                                       layer_model="ks.webhooks.configuration",
                                                                       woo_id=0,
                                                                       message=str(webhooks_response.text))
                total_api_calls = webhooks_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="webhook",
                                                               instance=wc_instance,
                                                               operation_flow="woo_to_odoo",
                                                               layer_model="ks.webhooks.configuration",
                                                               woo_id=0,
                                                               message=str(e))

        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="webhook",
                                                               operation_flow="woo_to_odoo",
                                                               instance=wc_instance,
                                                               layer_model="ks.webhooks.configuration",
                                                               woo_id=0,
                                                               message="Fetch of Webhooks successful")
            return ks_all_webhooks

    def ks_get_specific_webhooks(self, wc_instance, webhook_id):
        """
        Retrieve Specific Webhooks data from woocommerce
        :param instance_id: Id of instance for whose webhook has to be retrived
        :param webhook_id: id of webhook to retrieve data
        :return: dictionary
        """
        try:
            ks_webhook_data = None
            wcapi = wc_instance.ks_woo_api_authentication()
            webhook_response = wcapi.get("webhooks/%s" % webhook_id)
            if webhook_response.status_code in [200, 201]:
                ks_webhook_data = webhook_response.json()
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="webhook",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=wc_instance,
                                                                   layer_model="ks.webhooks.configuration",
                                                                   woo_id=0,
                                                                   message=str(webhook_response.text))

        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="webhook",
                                                               instance=wc_instance,
                                                               operation_flow="woo_to_odoo",
                                                               layer_model="ks.webhooks.configuration",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="webhook",
                                                               operation_flow="woo_to_odoo",
                                                               instance=wc_instance,
                                                               layer_model="ks.webhooks.configuration",
                                                               woo_id=ks_webhook_data.get("id", 0),
                                                               message="Fetch of Webhook successful")
            return ks_webhook_data

    def ks_create_webhook(self, wc_instance, data):
        """
        This will Create the Webhook on WooCommerce Instance
        :param wc_instance:  Id of instance for whose webhook has to be created
        :param data: JSON data to be used for creation of webhook
        :return: dictionary of json response creation data
        """
        try:
            ks_webhook_data = None
            wcapi = wc_instance.ks_woo_api_authentication()
            webhook_response = wcapi.post("webhooks", data)
            if webhook_response.status_code in [200, 201]:
                ks_webhook_data = webhook_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_odoo",
                                                                   status="success",
                                                                   type="webhook",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=wc_instance,
                                                                   layer_model="ks.webhooks.configuration",
                                                                   woo_id=ks_webhook_data.get("id", 0),
                                                                   message="Create of Webhook successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="webhook",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=wc_instance,
                                                                   layer_model="ks.webhooks.configuration",
                                                                   woo_id=0,
                                                                   message=str(webhook_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="webhook",
                                                               instance=wc_instance,
                                                               operation_flow="odoo_to_woo",
                                                               layer_model="ks.webhooks.configuration",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            return ks_webhook_data

    def ks_update_webhook(self, wc_instance, webhook_id, data):
        """
        This will Update a webhook record on WooCommerce Instance

        :param wc_instance: Id of instance for whose webhook has to be updated
        :param webhook_id: Id of webhook for its updation
        :param data: JSON data to be used for updation of webhook
        :return: json response
        """
        try:
            ks_webhook_data = None
            wcapi = wc_instance.ks_woo_api_authentication()
            webhook_response = wcapi.put("webhooks/%s" % webhook_id, data)
            if webhook_response.status_code in [200, 201]:
                ks_webhook_data = webhook_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_odoo",
                                                                   status="success",
                                                                   type="webhook",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=wc_instance,
                                                                   layer_model="ks.webhooks.configuration",
                                                                   woo_id=ks_webhook_data.get("id", 0),
                                                                   message="Update of Webhook successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="webhook",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=wc_instance,
                                                                   layer_model="ks.webhooks.configuration",
                                                                   woo_id=0,
                                                                   message=str(webhook_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="webhook",
                                                               instance=wc_instance,
                                                               operation_flow="odoo_to_woo",
                                                               layer_model="ks.webhooks.configuration",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            return ks_webhook_data
