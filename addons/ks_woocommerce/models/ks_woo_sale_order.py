# -*- coding: utf-8 -*-

import datetime
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class KsSaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    ks_woo_order_id = fields.Integer('Woocommerce Id', readonly=True, default=0, copy=False,
                                     help="Displays WooCommerce ID")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", readonly=False,
                                     help=_("WooCommerce Connector Instance reference"))
    ks_woo_status = fields.Selection([('on-hold', 'On-Hold'), ('pending', 'Pending'), ('processing', 'Processing'),
                                      ('cancelled', 'Cancelled'), ('refunded', 'Refunded'), ('completed', 'Completed'),
                                      ('failed', 'Failed')],
                                     string="Woo Status", default='pending', copy=False,
                                     help="Displays WooCommerce Order Status")
    ks_woo_coupons = fields.Many2many('ks.woo.coupons', string="WooCommerce Coupons", readonly=True, copy=False,
                                      help="Displays WooCommerce Order Coupons")
    ks_woo_payment_gateway = fields.Many2one('ks.woo.payment.gateway', string="Woo Payment Gateway", readonly=True,
                                             copy=False, help="Displays WooCommerce Order Payment Gateway")
    ks_date_created = fields.Datetime('Created On', copy=False,
                                      readonly=True,
                                      help="Created On: Date on which the WooCommerce Sale Order has been created")
    ks_date_updated = fields.Datetime('Updated On', copy=False,
                                      readonly=True,
                                      help="Updated On: Date on which the WooCommerce Sale Order has been last updated")
    ks_customer_ip_address = fields.Char(string='Customer IP', readonly=True, copy=False,
                                         help="Customer IP: WooCommerce Customer's IP address")
    ks_woo_transaction_id = fields.Char(string='Transaction Id', readonly=True, copy=False,
                                        help="Transaction Id: Unique transaction ID of WooCommerce Sale Order")
    ks_sync_states = fields.Boolean(string="Sync States",store=True,compute='compute_sync_status', readonly=True)

    ks_sync_date = fields.Datetime('Modified On', readonly=True,
                                   help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On', readonly=True)
    ks_sync_status = fields.Boolean('Sync Status', store= True, compute='sync_update', default=False)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.depends('ks_sync_date')
    def sync_update(self):
        for rec in self:
            if rec.ks_last_exported_date and rec.ks_sync_date:
                ks_reduced_ks_sync_time = rec.ks_last_exported_date - datetime.timedelta(seconds=5)
                ks_increased_ks_sync_time = rec.ks_last_exported_date + datetime.timedelta(seconds=5)
                if ks_reduced_ks_sync_time < rec.ks_sync_date < ks_increased_ks_sync_time:
                    rec.ks_sync_status = True
                else:
                    rec.ks_sync_status = False
            else:
                rec.ks_sync_status = False

    def write(self, values):
        for rec in self:
            if rec.ks_woo_order_id:
                values.update({'ks_sync_date': datetime.datetime.now()})
        super(KsSaleOrderInherit, self).write(values)

    def action_confirm(self):
        res = super(KsSaleOrderInherit, self).action_confirm()
        for order in self:
            if order.ks_date_created:
                if order.ks_woo_order_id:
                    order.ks_sync_date = datetime.datetime.now()
                    order.ks_last_exported_date = order.ks_sync_date
                    order.date_order = order.ks_date_created
                    order.sync_update()
        return res

    @api.onchange('ks_woo_status')
    def ks_update_status_on_woocommerce(self):
        """
        Update the Order status on the Woocommerce when updated on Odoo
        :return: None
        """
        for rec in self:
            if rec.ks_wc_instance.ks_auto_order_status_update_to_woo and rec.ks_woo_order_id:
                rec.ks_update_woo_order_status()

    @api.depends('ks_date_created','ks_date_updated','ks_sync_date')
    def compute_sync_status(self):
        if self:
            for rec in self:
                if not rec.ks_date_created and not rec.ks_date_updated:
                    rec.ks_sync_states = False

                elif rec.ks_date_updated >= rec.write_date \
                        or (abs(rec.ks_date_updated - rec.write_date).total_seconds() / 60) < 2:
                    rec.ks_sync_states = True

                else:
                    rec.ks_sync_states = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ks_wc_instance') and vals.get('ks_woo_order_id'):
                woo_instance = self.env['ks.woo.connector.instance'].search([('id', '=', vals.get('ks_wc_instance'))])
                if woo_instance and not woo_instance.ks_default_order_prefix:
                    woo_prefix = woo_instance.ks_custom_order_prefix.upper()
                    vals['name'] = woo_prefix + ' #' + str(vals.get('ks_woo_order_id'))
        return super(KsSaleOrderInherit, self).create(vals)

    def ks_cancel_sale_order_in_woo(self):
        self.ensure_one()
        if self.ks_wc_instance and self.ks_wc_instance.ks_instance_state == 'active':
            try:
                wcapi = self.ks_wc_instance.ks_woo_api_authentication()
                if wcapi.get("").status_code in [200, 201]:
                    if self.ks_wc_instance.ks_instance_state == 'active':
                        woo_cancel_response = wcapi.put("orders/%s" % self.ks_woo_order_id, {"status": "cancelled"})
                        if woo_cancel_response.status_code in [200, 201]:
                            self.ks_woo_status = 'cancelled'
                            woo_cancel_status = 'success'
                        else:
                            woo_cancel_status = 'failed'
                        self.env['ks.woo.logger'].ks_create_log_param(
                            ks_woo_id=self.ks_woo_order_id,
                            ks_status=woo_cancel_status,
                            ks_type='order',
                            ks_record_id=self.id,
                            ks_woo_instance=self.ks_wc_instance,
                            ks_operation_flow='odoo_to_woo',
                            ks_operation_performed='cancel',
                            ks_message='Order [' + self.name + '] has been succesfully cancelled' if woo_cancel_status == 'success' else 'The cancel operation failed for Order [' + self.name + '] due to ' + eval(
                                woo_cancel_response.text).get('message'),
                        )
                    else:
                        return self.env['ks.message.wizard'].ks_pop_up_message(names='Error',
                                                                               message='The instance must be in '
                                                                                       'active state to perform '
                                                                                       'the operations')
            except ConnectionError:
                raise ValidationError("Couldn't Connect the Instance[ %s ]  !! Please check the network connectivity"
                                      " or the configuration parameters are not "
                                      "correctly set" % self.ks_wc_instance.ks_name)

    def ks_woo_import_order_create(self, order_data, instance, queue_record=False):
        try:
            order_json = self.ks_prepare_import_json_data(order_data, instance)
            if order_json:
                order_record = self.create(order_json)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(order_data, order_record,
                                                                                 'ks_woo_order_id')
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                   ks_model='sale.order',
                                                                   ks_layer_model='sale.order',
                                                                   ks_message="Sale order import create success",
                                                                   ks_status="success",
                                                                   ks_type="order",
                                                                   ks_record_id=order_record.id,
                                                                   ks_operation_flow="woo_to_odoo",
                                                                   ks_woo_id=order_data.get(
                                                                       "id", 0),
                                                                   ks_woo_instance=instance)
                order_record.ks_sync_date = datetime.datetime.now()
                order_record.ks_last_exported_date = order_record.ks_sync_date
                order_record.sync_update()

                return order_record
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                               ks_model='sale.order',
                                                               ks_layer_model='sale.order',
                                                               ks_message=str(e),
                                                               ks_status="failed",
                                                               ks_type="order",
                                                               ks_record_id=0,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=order_data.get(
                                                                   "id", 0),
                                                               ks_woo_instance=instance)

    def ks_pull_order_status(self):
        if self.ks_woo_order_id:
            orders_json_records = self.env['sale.order'].ks_get_all_woo_orders(instance=self.ks_wc_instance, include=self.ks_woo_order_id)[0]
            self.ks_woo_import_order_update(orders_json_records, update=True)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                               ks_model='sale.order',
                                                               ks_layer_model='sale.order',
                                                               ks_message="Order Status Updated",
                                                               ks_status="success",
                                                               ks_type="order",
                                                               ks_record_id=self.id,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=self.ks_woo_order_id,
                                                               ks_woo_instance=self.ks_wc_instance)
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                               ks_model='sale.order',
                                                               ks_layer_model='sale.order',
                                                               ks_message="Order Isn't syned, therefore status can't be updated",
                                                               ks_status="failed",
                                                               ks_type="order",
                                                               ks_record_id=self.id,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=0,
                                                               ks_woo_instance=self.ks_wc_instance)

    def ks_woo_import_order_update(self, order_data, queue_record=False, update=False):
        try:
            if self.state in ["draft", "sent", "cancel"]:
                order_json = self.ks_prepare_import_json_data(order_data, self.ks_wc_instance)
                if order_json:
                    self.write(order_json)
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(order_data, self,
                                                                                     'ks_woo_order_id')
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                       ks_model='sale.order',
                                                                       ks_layer_model='sale.order',
                                                                       ks_message="Sale order import update success",
                                                                       ks_status="success",
                                                                       ks_type="order",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=order_data.get(
                                                                           "id", 0),
                                                                       ks_woo_instance=self.ks_wc_instance)
                    self.ks_sync_date = datetime.datetime.now()
                    self.ks_last_exported_date = self.ks_sync_date
                    self.sync_update()
                    return self
            else:
                if self.state in ['sale','done'] and self.ks_woo_order_id and update:
                    self.write({
                        'ks_woo_status':order_data.get('status'),
                    })
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(order_data, self,
                                                                                     'ks_woo_order_id')
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                       ks_model='sale.order',
                                                                       ks_layer_model='sale.order',
                                                                       ks_message="Sale order Status update success",
                                                                       ks_status="success",
                                                                       ks_type="order",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=order_data.get(
                                                                           "id", 0),
                                                                       ks_woo_instance=self.ks_wc_instance)
                    self.ks_sync_date = datetime.datetime.now()
                    self.ks_last_exported_date = self.ks_sync_date
                    self.sync_update()
                    return self
                else:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                       ks_model='sale.order',
                                                                       ks_layer_model='sale.order',
                                                                       ks_message="Order already processed, So we cant update it",
                                                                       ks_status="failed",
                                                                       ks_type="order",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=order_data.get(
                                                                           "id", 0),
                                                                       ks_woo_instance=self.ks_wc_instance)
                self.ks_sync_date = datetime.datetime.now()
                self.ks_last_exported_date = self.ks_sync_date
                self.sync_update()

        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                               ks_model='sale.order',
                                                               ks_layer_model='sale.order',
                                                               ks_message=str(e),
                                                               ks_status="failed",
                                                               ks_type="order",
                                                               ks_record_id=self.id,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=order_data.get(
                                                                   "id", 0),
                                                               ks_woo_instance=self.ks_wc_instance)

    def ks_get_all_woo_orders(self, instance, include=False, date_before=False, date_after=False, status=False):
        """
           :param wc_api: The WooCommerce API instance
           :instance_id: Id of instance whose order have to be retrieved
           :return: List of Dictionary of get Woo Products
           :rtype: List
        """
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = []
        if include:
            params = {'per_page': per_page,
                      'page': page,
                      'include': include}
        elif date_before or date_after:
            params = {'per_page': per_page,
                      'page': page}
            if date_before:
                params.update({
                    'before': date_before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                })
            if date_after:
                params.update({
                    'after': date_after.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                })
        else:
            params = {'per_page': per_page,
                      'page': page}
        if status:
            params.update({
                'status': status
            })
        try:
            while multi_api_call:
                wc_api = instance.ks_woo_api_authentication()
                orders_response = wc_api.get("orders", params=params)
                if orders_response.status_code in [200, 201]:
                    all_retrieved_data.extend(orders_response.json())
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="order",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       message=str(orders_response.text))
                total_api_calls = orders_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                    params.update({'page': page})
                else:
                    multi_api_call = False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="order",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="order",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance,
                                                               woo_id=0,
                                                               message="Fetch of Orders successful")
            return all_retrieved_data

    def ks_export_order_to_woo(self, queue_record=False):
        for order in self:
            if order.ks_wc_instance and order.ks_wc_instance.ks_instance_state == 'active':
                try:
                    wcapi = order.ks_wc_instance.ks_woo_api_authentication()
                    woo_response = None
                    if wcapi.get("").status_code:
                        if not order.ks_woo_order_id:
                            json_data = order.ks_prepare_export_json_data()
                            if json_data:
                                woo_response = wcapi.post("orders", json_data)
                                if woo_response.status_code in [200, 201]:
                                    woo_order_record = woo_response.json()
                                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(woo_order_record,
                                                                                                     order,
                                                                                                     'ks_woo_order_id')
                                    self.env['ks.woo.logger'].ks_create_odoo_log_param(
                                        ks_operation_performed="create_woo",
                                        ks_model='sale.order',
                                        ks_layer_model='sale.order',
                                        ks_message='''Order export success''',
                                        ks_status="success",
                                        ks_type="order",
                                        ks_record_id=self.id,
                                        ks_operation_flow="odoo_to_woo",
                                        ks_woo_id=woo_order_record.get(
                                            "id"),
                                        ks_woo_instance=self.ks_wc_instance)
                                    order.ks_sync_date = datetime.datetime.now()
                                    order.ks_last_exported_date = order.ks_sync_date
                                    order.sync_update()
                                    return woo_order_record
                                else:
                                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                                       ks_model='sale.order',
                                                                                       ks_layer_model='sale.order',
                                                                                       ks_message='''Order export failed''',
                                                                                       ks_status="failed",
                                                                                       ks_type="order",
                                                                                       ks_record_id=self.id,
                                                                                       ks_operation_flow="odoo_to_woo",
                                                                                       ks_woo_id=0,
                                                                                       ks_woo_instance=self.ks_wc_instance)
                            else:
                                if queue_record:
                                    queue_record.ks_update_failed_state()
                                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                                   ks_model='sale.order',
                                                                                   ks_layer_model='sale.order',
                                                                                   ks_message='Order export failed [' + order.name + '] make sure all you products/customers are synced',
                                                                                   ks_status="failed",
                                                                                   ks_type="order",
                                                                                   ks_record_id=self.id,
                                                                                   ks_operation_flow="odoo_to_woo",
                                                                                   ks_woo_id=0,
                                                                                   ks_woo_instance=self.ks_wc_instance)
                        else:
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                               ks_model='sale.order',
                                                                               ks_layer_model='sale.order',
                                                                               ks_message='Order [' + order.name + '] is already exported',
                                                                               ks_status="failed",
                                                                               ks_type="order",
                                                                               ks_record_id=self.id,
                                                                               ks_operation_flow="odoo_to_woo",
                                                                               ks_woo_id=order.ks_woo_order_id,
                                                                               ks_woo_instance=self.ks_wc_instance)
                            return {'id': order.ks_woo_order_id}
                    return False

                except Exception as e:
                    if queue_record:
                        queue_record.ks_update_failed_state()
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                       ks_model='sale.order',
                                                                       ks_layer_model='sale.order',
                                                                       ks_message=str(e),
                                                                       ks_status="failed",
                                                                       ks_type="order",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="odoo_to_woo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=self.ks_wc_instance)

    def ks_get_woo_orders(self, order_id, instance):
        """
           :param order_id:
           :param instance:
           :param wc_api: The WooCommerce API instance
           :instance_id: Id of instance whose order have to be get
           :category_id: Id of order specific whose order details has to be get
           :return: Dictionary of get Woo order
           :rtype: dict
        """
        try:
            order_response_record = None
            wc_api = instance.ks_woo_api_authentication()
            order_response = wc_api.get("orders/%s" % order_id)
            if order_response.status_code in [200, 201]:
                order_response_record = order_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="order",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=order_response_record.get("id", 0),
                                                                   message="Fetch of Orders successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="order",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   message=str(order_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="order",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            return order_response_record

    def ks_post_woo_order(self, data, instance):
        """
           :param wc_api: The WooCommerce API instance
           :data: JSON data for which order has to be created
           :instance_id: Id of instance whose order have to be created
           :return: Dictionary of created Woo order
           :rtype: dict
        """
        try:
            order_response_record = None
            wc_api = instance.ks_woo_api_authentication()
            order_response = wc_api.post("orders", data)
            if order_response.status_code in [200, 201]:
                order_response_record = order_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="order",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=order_response_record.get("id", 0),
                                                                   message="Create of Orders successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="order",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   message=str(order_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="order",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            return order_response_record

    def ks_update_woo_order(self, order_id, data, instance):
        """
           :param wc_api: The WooCommerce API instance
           :data: JSON data for which order has to be updated
           :instance_id: Id of instance whose order have to be updated
           :product_id: Id of order for which data has to be updated
           :return: Boolean True if: Data Successfully updated else: False
        """
        try:
            order_response_record = None
            wc_api = instance.ks_woo_api_authentication()
            order_response = wc_api.put("orders/%s" % order_id, data)
            if order_response.status_code in [200, 201]:
                order_response_record = order_response.json()
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="order",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   message=str(order_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="order",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_post",
                                                               status="success",
                                                               type="order",
                                                               operation_flow="odoo_to_woo",
                                                               instance=instance,
                                                               woo_id=order_response_record.get("id", 0),
                                                               message="Update of Orders successful")
            return order_response_record

    def _get_product_ids(self, instance, json_data):
        product_id = json_data.get("product_id")
        variation_id = json_data.get("variation_id")
        woo_product_json = self.env['ks.woo.product.template'].ks_woo_get_product(product_id, instance)
        odoo_product = self.env['ks.woo.product.template'].ks_manage_woo_product_template_import(instance,
                                                                                                 woo_product_json)
        if not variation_id:
            return odoo_product.ks_product_template.product_variant_ids.filtered(
                lambda x: x.id == odoo_product.ks_product_template.product_variant_id.id)
        else:
            return odoo_product.ks_product_template.product_variant_ids.ks_product_variant.search(
                [('ks_wc_instance', '=', instance.id),
                 ('ks_woo_variant_id', '=', variation_id)]).ks_product_variant

    def _prepare_guest_customer_data(self, address, type, instance=False):
        if address and not self.env['res.partner'].check_empty_dict(address):
            address_data = self.env['ks.woo.partner'].ks_convert_odoo_compatible_data(address,
                                                                                      type, instance=instance)
            return address_data
        return False

    def _get_customer_id(self, woo_cust_id, instance_id, invoice_address=False, shipping_address=False, meta_data=False):
        json_data = {"billing": invoice_address,
                     "shipping": shipping_address}
        if not woo_cust_id:
            if instance_id.ks_is_named_guest_customer:
                # Handling guest customer as individual RES PARTNER
                i_address = self.env['res.partner'].check_empty_dict(invoice_address)
                s_address = self.env['res.partner'].check_empty_dict(shipping_address)
                woo_customer_exist = ""
                if not i_address and not s_address:
                    if instance_id.ks_customer_address == 'billing':
                        woo_customer_exist = self.env['res.partner'].ks_manage_woo_guest_customer_import("billing",
                                                                                                         invoice_address,
                                                                                                         instance=instance_id,meta_data=meta_data)
                    elif instance_id.ks_customer_address == 'shipping':
                        woo_customer_exist = self.env['res.partner'].ks_manage_woo_guest_customer_import("shipping",
                                                                                                         shipping_address,
                                                                                                         instance=instance_id,meta_data=meta_data)
                else:
                    if not i_address:
                        woo_customer_exist = self.env['res.partner'].ks_manage_woo_guest_customer_import("billing",
                                                                                                         invoice_address,
                                                                                                         instance=instance_id,meta_data=meta_data)
                    elif not s_address:
                        woo_customer_exist = self.env['res.partner'].ks_manage_woo_guest_customer_import("shipping",
                                                                                                         shipping_address,
                                                                                                         instance=instance_id,meta_data=meta_data)
                if woo_customer_exist:
                    billing_address = self._prepare_guest_customer_data(invoice_address, 'billing',
                                                                        instance=instance_id)
                    shipping_address = self._prepare_guest_customer_data(shipping_address, 'shipping',
                                                                         instance=instance_id)
                    if billing_address:
                        mapped_odoo_customer = self.env['res.partner'].ks_handle_customer_address(woo_customer_exist,
                                                                                                  billing_address,
                                                                                                  instance=instance_id)
                        woo_customer_exist = mapped_odoo_customer
                    if shipping_address:
                        mapped_odoo_customer = self.env['res.partner'].ks_handle_customer_address(woo_customer_exist,
                                                                                                  shipping_address,
                                                                                                  instance=instance_id)
                        woo_customer_exist = mapped_odoo_customer
            else:  # Hanlding guest customer as child of ODOO GUEST CUSTOMER
                woo_customer_exist = self.env.ref('ks_woocommerce.ks_woo_guest_customers')
                billing_address = self._prepare_guest_customer_data(invoice_address, 'billing', instance=instance_id)
                shipping_address = self._prepare_guest_customer_data(shipping_address, 'shipping', instance=instance_id)
                if billing_address:
                    mapped_odoo_customer = self.env['res.partner'].ks_handle_customer_address(woo_customer_exist,
                                                                                              billing_address,
                                                                                              instance=instance_id)
                    woo_customer_exist = mapped_odoo_customer

                if shipping_address:
                    mapped_odoo_customer = self.env['res.partner'].ks_handle_customer_address(woo_customer_exist,
                                                                                              shipping_address,
                                                                                              instance=instance_id)
                    woo_customer_exist = mapped_odoo_customer
        else:
            customer_data = self.env['ks.woo.partner'].ks_woo_get_customer(woo_cust_id,
                                                                           instance_id)
            if customer_data:
                odoo_customer = self.env['ks.woo.partner'].ks_manage_woo_customer_import(instance_id, customer_data)
                billing_data = self._prepare_guest_customer_data(invoice_address, 'billing', instance=instance_id)
                if billing_data:
                    mapped_odoo_customer = self.env['res.partner'].ks_handle_customer_address(odoo_customer,
                                                                                              billing_data,
                                                                                              instance=instance_id)
                    woo_customer_exist = mapped_odoo_customer
                shipping_data = self._prepare_guest_customer_data(shipping_address, 'shipping', instance=instance_id)
                if shipping_data:
                    mapped_odoo_customer = self.env['res.partner'].ks_handle_customer_address(odoo_customer,
                                                                                              shipping_data,
                                                                                              instance=instance_id)
                    woo_customer_exist = mapped_odoo_customer
            else:
                woo_customer_exist = self.env.ref('ks_woocommerce.ks_woo_guest_customers')
        return woo_customer_exist if woo_customer_exist else False

    def _get_payment_gateway(self, each_record, instance):
        if each_record.get('payment_method') and each_record.get('payment_method_title'):
            payment_gateway = self.env['ks.woo.payment.gateway'].search([
                ('ks_woo_pg_id', '=', each_record.get('payment_method')), ('ks_wc_instance', '=', instance.id)],
                limit=1)
            if not payment_gateway:
                payment_gateway = self.env['ks.woo.payment.gateway'].create({
                    'ks_woo_pg_id': each_record.get('payment_method') or '',
                    'ks_wc_instance': instance.id,
                    'ks_title': each_record.get('payment_method_title') or ''
                })
            return payment_gateway.id

    def _get_woo_coupons(self, woo_coupon_lines, instance):
        coupon_ids = []
        for each_coupon in woo_coupon_lines:
            coupon_exist_in_odoo = self.env['ks.woo.coupons'].search(
                [('ks_coupon_code', '=', each_coupon.get('code')),
                 ('ks_wc_instance', '=', instance.id)],
                limit=1)
            if coupon_exist_in_odoo:
                coupon_ids.append(coupon_exist_in_odoo.id)
            else:
                coupon_id = self.env['ks.woo.coupons'].create({
                    'ks_woo_coupon_id': each_coupon.get('id'),
                    'ks_amount': float(each_coupon.get('discount') or 0),
                    'ks_coupon_code': each_coupon.get('code') or '',
                    'ks_wc_instance': instance.id
                }).id
                coupon_ids.append(coupon_id)
        return coupon_ids

    def get_tax_ids(self, tax, order_line_tax, instance):
        if tax:
            taxes = []
            for ol_tax in order_line_tax:
                for each_record in tax:
                    tax_exist = self.env['account.tax'].search([('name', '=', each_record.get('rate_code')),
                                                                ('type_tax_use', '=', 'sale')], limit=1)
                    try:
                        wc_api = instance.ks_woo_api_authentication()
                        woo_tax_response = wc_api.get('taxes/%s' % each_record.get('rate_id'))
                        if woo_tax_response.status_code in [200, 201]:
                            woo_tax_record = woo_tax_response.json()
                            tax_value = self.env['ir.config_parameter'].sudo().get_param(
                                'account.show_line_subtotals_tax_selection')
                            if tax_value == 'tax_excluded':
                                price_include = False
                            elif tax_value == 'tax_included':
                                price_include = True
                            else:
                                price_include = False
                            woo_tax_data = {
                                'name': each_record.get('rate_code'),
                                'ks_woo_id': woo_tax_record.get('id'),
                                'ks_wc_instance': instance.id,
                                'amount': float(woo_tax_record.get('rate') or 0),
                                'amount_type': 'percent',
                                'company_id': instance.ks_company_id.id,
                                'type_tax_use': 'sale',
                                'active': True,
                                'price_include': price_include,
                            }
                            if tax_exist:
                                tax_exist.write(woo_tax_data)
                            else:
                                tax_exist = self.env['account.tax'].create(woo_tax_data)
                            current_tax_total = float(each_record.get('tax_total') or 0)
                            if current_tax_total and ol_tax.get('id') == each_record.get('rate_id'):
                                taxes.append(tax_exist.id)
                    except Exception as e:
                        self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                      ks_woo_instance=instance,
                                                                      ks_record_id=0,
                                                                      ks_message='Create/Fetch of Taxes Failed',
                                                                      ks_woo_id=0,
                                                                      ks_operation_flow='woo_to_odoo',
                                                                      ks_status="failed",
                                                                      ks_type="system_status",
                                                                      ks_error=e)

            return taxes if taxes else []
        else:
            return []

    def _get_order_lines(self, order_json_data, instance):
        order_lines = []
        for each_record in order_json_data.get('line_items'):
            sale_order_exist = self.search([('ks_woo_order_id', '=', order_json_data.get('id')),
                                            ('ks_wc_instance', '=', instance.id)], limit=1)
            sale_order_line_exist = self.env['sale.order.line'].search(
                [('ks_woo_order_line_id', '=', each_record.get('id')),
                 ('order_id', '=', sale_order_exist.id)],
                limit=1)
            product = self._get_product_ids(instance, each_record)
            if product:
                ks_price_unit = float(
                    (float(each_record.get('subtotal') or 0) / int(each_record.get('quantity') or 1)) or 0)
                line_items_data = {
                    'ks_woo_order_line_id': each_record.get('id'),
                    'name': each_record.get('name'),
                    'product_id': product.id,
                    'product_uom_qty': each_record.get('quantity'),
                    'price_unit': ks_price_unit,
                    'product_uom': product.uom_id.id,
                    'tax_id': [(6, 0, self.get_tax_ids(order_json_data.get('tax_lines'), each_record.get('taxes'),
                                                       instance))],
                    'ks_discount_amount': float(
                        (float(each_record.get('subtotal') or 0) - float(each_record.get('total') or 0)) or 0)
                }
                if not line_items_data.get("tax_id") and line_items_data.get('taxes'):
                    line_items_data.update({
                        "price_tax": each_record.get("subtotal_tax")
                    })
                if sale_order_line_exist:
                    order_lines.append((1, sale_order_line_exist.id, line_items_data))
                else:
                    order_lines.append((0, 0, line_items_data))
            else:
                raise TypeError(
                    "Product Does not exist on woocommerce with woo ID : %s" % each_record.get("product_id"))

        for each_rec in order_json_data.get('fee_lines'):
            sale_order_exist = self.search([('ks_woo_order_id', '=', order_json_data.get('id')),
                                            ('ks_wc_instance', '=', instance.id)], limit=1)
            sale_order_line_exist = self.env['sale.order.line'].search(
                [('ks_woo_order_line_id', '=', each_rec.get('id')),
                 ('order_id', '=', sale_order_exist.id)],
                limit=1)

            fee_lines_data = {
                'ks_woo_order_line_id': each_rec.get('id'),
                'name': each_rec.get('name'),
                'product_id': self.env.ref('ks_woocommerce.ks_woo_fees').id,
                'product_uom': self.env.ref('ks_woocommerce.ks_woo_fees').uom_id.id,
                'product_uom_qty': 1,
                'price_unit': float(each_rec.get('amount') or each_rec.get('total') or 0),
                'tax_id': [(6, 0, self.get_tax_ids(order_json_data.get('tax_lines'), each_rec.get('taxes'),
                                                   instance))]
            }
            if not fee_lines_data.get("tax_id") and each_rec.get('taxes'):
                fee_lines_data.update({
                    "price_tax": each_rec.get("subtotal_tax")
                })
            if sale_order_line_exist:
                order_lines.append((1, sale_order_line_exist.id, fee_lines_data))
            else:
                order_lines.append((0, 0, fee_lines_data))

        for each_rec in order_json_data.get('shipping_lines'):
            sale_order_exist = self.search([('ks_woo_order_id', '=', order_json_data.get('id')),
                                            ('ks_wc_instance', '=', instance.id)], limit=1)
            sale_order_line_exist = self.env['sale.order.line'].search(
                [('ks_woo_order_line_id', '=', each_rec.get('id')),
                 ('order_id', '=', sale_order_exist.id)],
                limit=1)
            shipping_lines_data = {
                'ks_woo_order_line_id': each_rec.get('id'),
                'name': each_rec.get('method_id'),  # "[Woo]"
                'product_id': self.env.ref('ks_woocommerce.ks_woo_shipping_fees').id,
                'product_uom': self.env.ref('ks_woocommerce.ks_woo_shipping_fees').uom_id.id,
                'product_uom_qty': 1,
                'price_unit': float(each_rec.get('total') or 0),
                'tax_id': [(6, 0, self.get_tax_ids(order_json_data.get('tax_lines'), each_rec.get('taxes'),
                                                   instance))]
            }
            if not shipping_lines_data.get("tax_id") and each_rec.get('taxes'):
                shipping_lines_data.update({
                    "price_tax": each_rec.get("subtotal_tax")
                })
            if sale_order_line_exist:
                order_lines.append((1, sale_order_line_exist.id, shipping_lines_data))
            else:
                order_lines.append((0, 0, shipping_lines_data))
        return order_lines

    def _get_order_woo_lines(self, order_line_data):
        line_data = []
        for order_line in order_line_data:
            values = {
                "id": order_line.ks_woo_order_line_id,
                "name": order_line.name,
                "quantity": order_line.product_uom_qty,
                "subtotal": str(order_line.price_unit * order_line.product_uom_qty),
                "total": str(order_line.price_reduce_taxexcl * order_line.product_uom_qty),
                "sku": order_line.product_id.default_code if order_line.product_id.default_code else '',
            }
            if order_line.product_id:
                template = order_line.product_id.product_tmpl_id
                woo_template = self.env["ks.woo.product.template"].search(
                    [("ks_product_template", "=", template.id),
                     ("ks_wc_instance", "=", self.ks_wc_instance.id)])
                if woo_template and woo_template.ks_woo_product_id:
                    if woo_template.ks_woo_product_type == "simple":
                        values.update({
                            "product_id": woo_template.ks_woo_product_id,
                            "variation_id": 0,
                        })
                    else:
                        product_id = self.env["ks.woo.product.variant"].search(
                            [("ks_product_variant", "=", order_line.product_id.id),
                             ("ks_wc_instance", "=", self.ks_wc_instance.id)])
                        if product_id and product_id.ks_woo_variant_id:
                            values.update({
                                "product_id": woo_template.ks_woo_product_id,
                                "variation_id": product_id.ks_woo_variant_id,
                            })
                        else:
                            return False
                    line_data.append(values)
                else:
                    layer_product = self.env['ks.woo.product.template'].create_woo_record(self.ks_wc_instance, template,
                                                                                          export_to_woo=True)
                    if layer_product.ks_woo_product_type == "simple":
                        values.update({
                            "product_id": layer_product.ks_woo_product_id,
                            "variation_id": 0,
                        })
                    else:
                        product_id = self.env["ks.woo.product.variant"].search(
                            [("ks_product_variant", "=", order_line.product_id.id),
                             ("ks_wc_instance", "=", self.ks_wc_instance.id)])
                        if product_id and product_id.ks_woo_variant_id:
                            values.update({
                                "product_id": woo_template.ks_woo_product_id,
                                "variation_id": product_id.ks_woo_variant_id,
                            })
                        else:
                            return False
                    line_data.append(values)
        return line_data

    def ks_enqueue_sale_orders(self):
        try:
            orders = self.filtered(
                lambda x: x.ks_wc_instance != False and x.ks_wc_instance.ks_instance_state == "active")
            for order in orders:
                if not order.ks_woo_status == 'failed':
                    self.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=order.ks_wc_instance,
                                                                                  records=order)
                else:
                    return self.env["ks.message.wizard"].ks_pop_up_message(names='Error',
                                                                           message="Woo Status of Order MUST  NOT be Failed!")
            return self.env["ks.message.wizard"].ks_pop_up_message(names='Info',
                                                                   message="Orders with instance present have been sent to queue for syncing")
        except Exception as e:
            _logger.error(str(e))

    def ks_update_woo_order_status(self):
        for each_rec in self:
            if each_rec.ks_wc_instance and each_rec.ks_wc_instance.ks_instance_state == 'active':
                try:
                    if each_rec.ks_woo_order_id:
                        wc_api = each_rec.ks_wc_instance.ks_woo_api_authentication()
                        if wc_api.get("").status_code in [200, 201]:
                            woo_status_response = wc_api.put("orders/%s" % each_rec.ks_woo_order_id,
                                                             {"status": each_rec.ks_woo_status})
                            self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='update_woo',
                                                                          ks_type='order',
                                                                          ks_woo_instance=each_rec.ks_wc_instance,
                                                                          ks_record_id=each_rec.id,
                                                                          ks_message='Order [' + each_rec.name + ']  status has been succesfully updated' if woo_status_response.status_code in [
                                                                              200,
                                                                              201] else 'The status update operation failed for Order [' + each_rec.name + '] due to ' + eval(
                                                                              woo_status_response.text).get('message'),
                                                                          ks_woo_id=each_rec.ks_woo_order_id,
                                                                          ks_operation_flow='odoo_to_woo',
                                                                          ks_status='success' if woo_status_response.status_code in [
                                                                              200, 201] else 'failed')
                            each_rec.ks_sync_date = datetime.datetime.now()
                            each_rec.ks_last_exported_date = each_rec.ks_sync_date
                            each_rec.sync_update()
                        else:
                            self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='update',
                                                                          ks_type='system_status',
                                                                          ks_woo_instance=each_rec.ks_wc_instance,
                                                                          ks_record_id=each_rec.id,
                                                                          ks_message='Connection successful' if wc_api.get(
                                                                              "").status_code in [200,
                                                                                                  201] else wc_api.get(
                                                                              "").text,
                                                                          ks_woo_id=each_rec.ks_woo_order_id,
                                                                          ks_operation_flow='odoo_to_woo',
                                                                          ks_status='success' if wc_api.get(
                                                                              "").status_code in [200,
                                                                                                  201] else 'failed')
                    else:
                        self.env['ks.woo.logger'].ks_create_log_param(ks_woo_id=0,
                                                                      ks_operation_performed='update',
                                                                      ks_type='order',
                                                                      ks_woo_instance=self.ks_wc_instance,
                                                                      ks_record_id=each_rec.id,
                                                                      ks_message='"Sale Order update failed", Sale Order [' + each_rec.name + '] not synced yet',
                                                                      ks_operation_flow='odoo_to_woo',
                                                                      ks_status='failed')
                except ConnectionError:
                    self.env['ks.woo.logger'].ks_create_log_param(ks_woo_id=self.ks_woo_order_id.id,
                                                                  ks_operation_performed='update',
                                                                  ks_type='system_status',
                                                                  ks_woo_instance=self.ks_woo_order_id.ks_wc_instance,
                                                                  ks_record_id=each_rec.id,
                                                                  ks_message='Fatal Error Connection Error' + str(
                                                                      ConnectionError),
                                                                  ks_operation_flow='odoo_to_woo',
                                                                  ks_status='Failed')
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_log_param(ks_woo_id=self.ks_woo_order_id.id,
                                                                  ks_operation_performed='update',
                                                                  ks_type='system_status',
                                                                  ks_woo_instance=self.ks_woo_order_id.ks_wc_instance,
                                                                  ks_record_id=each_rec.id,
                                                                  ks_message='Order status update failed due to: ' + str(
                                                                      e),
                                                                  ks_operation_flow='odoo_to_woo',
                                                                  ks_status='Failed')
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_auto_update_wc_order_status(self, cron_id=False):
        try:
            if not cron_id:
                if self._context.get('params'):
                    cron_id = self.env["ir.cron"].browse(self._context.get('params').get('id'))
            else:
                cron_id = self.env["ir.cron"].browse(cron_id)
            instance_id = cron_id.ks_wc_instance
            if instance_id and instance_id.ks_instance_state == 'active':
                orders = self.search([("ks_wc_instance", "=", instance_id.id),
                                      ("ks_woo_order_id", "!=", 0)])
                orders.ks_update_woo_order_status()
        except Exception as e:
            _logger.info(str(e))

    def ks_auto_import_wc_order(self, cron_id=False):
        try:
            if not cron_id:
                if self._context.get('params'):
                    cron_id = self.env["ir.cron"].browse(self._context.get('params').get('id'))
            else:
                cron_id = self.env["ir.cron"].browse(cron_id)
            instance_id = cron_id.ks_wc_instance
            if instance_id and instance_id.ks_instance_state == 'active':
                order_status = ','.join(instance_id.ks_order_status.mapped('status'))
                date_before = instance_id.ks_order_date_before if instance_id.ks_order_date_before else False
                date_after = instance_id.ks_order_date_after if instance_id.ks_order_date_after else False
                orders_json_records = self.env['sale.order'].ks_get_all_woo_orders(
                    instance=instance_id, status=order_status,date_after=date_after,date_before=date_before)
                for order_data in orders_json_records:
                    order_record_exist = self.env['sale.order'].search(
                        [('ks_wc_instance', '=', instance_id.id),
                         ('ks_woo_order_id', '=', order_data.get("id"))])
                    if order_record_exist:
                        order_record_exist.ks_woo_import_order_update(order_data)
                    else:
                        order_record_exist.ks_woo_import_order_create(
                            order_data, instance_id)
                    self.ks_sync_date = datetime.datetime.now()
                    self.ks_last_exported_date = self.ks_sync_date
                    self.sync_update()
        except Exception as e:
            _logger.info(str(e))

    def ks_prepare_import_json_data(self, order_json_data, instance):
        currency_id = instance.ks_woo_currency
        data = {
            'ks_woo_order_id': order_json_data.get("id"),
            'ks_wc_instance': instance.id,
            'ks_woo_status': order_json_data.get("status"),
            'ks_customer_ip_address': order_json_data.get("customer_ip_address"),
            'ks_woo_transaction_id': order_json_data.get("transaction_id"),
            'note': order_json_data.get('customer_note'),
            'currency_id': currency_id.id,
            'order_line': self._get_order_lines(order_json_data, instance),
            'warehouse_id': instance.ks_warehouse.id,
            'company_id': instance.ks_company_id.id,
            'team_id': instance.ks_sales_team.id,
            'payment_term_id': instance.ks_payment_term_id.id,
            'ks_woo_payment_gateway': self._get_payment_gateway(order_json_data, instance)
        }
        if self.user_id.id != instance.ks_sales_person.id:
            data.update({
                'user_id': instance.ks_sales_person.id,
            })
        odoo_partner = self._get_customer_id(order_json_data.get('customer_id'), instance,
                                             order_json_data.get("billing", {}),
                                             order_json_data.get("shipping", {}), order_json_data.get('meta_data'))
        is_billing = self.env['res.partner'].check_empty_dict(order_json_data['billing'])
        is_shipping = self.env['res.partner'].check_empty_dict(order_json_data['shipping'])
        data.update({
            'partner_id': odoo_partner.id,
            'partner_invoice_id': self.get_shipping_billing_address(odoo_partner, 'billing', order_json_data.get(
                "billing"), instance=instance).id if not is_billing else odoo_partner.id,
            'partner_shipping_id': self.get_shipping_billing_address(odoo_partner, 'shipping', order_json_data.get(
                "shipping"), instance=instance).id if not is_shipping else odoo_partner.id,
        })
        coupon_ids = self._get_woo_coupons(order_json_data.get('coupon_lines'), instance)
        data.update({
            'ks_woo_coupons': [(6, 0, coupon_ids)] if coupon_ids else False
        })
        if data:
            auto_workflow = self.get_auto_worflow(data.get("ks_woo_payment_gateway"), data.get("ks_woo_status"),
                                                  instance)
            if not auto_workflow:
                auto_workflow = self.env.ref('ks_base_connector.ks_automatic_validation')
            data.update({
                "ks_auto_workflow_id": auto_workflow.id
            })

        if instance and instance.ks_want_maps:
            if order_json_data.get("meta_data"):
                sale_order_maps = instance.ks_meta_mapping_ids.search([('ks_wc_instance', '=', instance.id),
                                                                       ('ks_active', '=', True),
                                                                       ('ks_model_id.model', '=', 'sale.order')
                                                                       ])
                for map in sale_order_maps:
                    odoo_field = map.ks_fields.name
                    json_key = map.ks_key
                    for meta_data in order_json_data.get("meta_data"):
                        if meta_data.get("key", '') == json_key:
                            data.update({
                                odoo_field: meta_data.get("value", '')
                            })

        return data

    # The objective is to populate appropriate shipping and billing address - as received in Order json data
    def get_shipping_billing_address(self, odoo_partner, type, address, instance=False):
        if odoo_partner:
            json_address = self._prepare_guest_customer_data(address, type)
            domain = [('parent_id', '=', odoo_partner.id),
                      ("name", '=ilike', json_address.get("name")),
                      ("street", '=ilike', json_address.get("street")),
                      ("street2", '=ilike', json_address.get("street2")),
                      ("city", "=ilike", json_address.get("city")),
                      ("zip", "=ilike", json_address.get("zip")),
                      ("state_id", '=', json_address.get("state_id")),
                      ("country_id", '=', json_address.get("country_id")),
                      ("email", '=ilike', json_address.get("email")),
                      ("phone", '=ilike', json_address.get("phone"))]
            if instance:
                domain.append(('company_id', '=', instance.ks_company_id.id))
            mapped_child = odoo_partner.child_ids.search(domain, limit=1)
            return mapped_child

    def get_auto_worflow(self, payment_gateway_id, order_status, instance):
        auto_workflow = False
        if instance.ks_order_import_type == "status":
            auto_workflow = self.env['ks.woo.auto.sale.workflow.configuration'].search([
                ("ks_wc_instance", "=", instance.id),
                ("ks_woo_order_status.status", "=", order_status)
            ], limit=1)
            auto_workflow = auto_workflow.ks_sale_workflow_id
        elif instance.ks_order_import_type == "payment_gateway":
            auto_workflow = self.env['ks.woo.auto.sale.workflow.configuration'].search([
                ("ks_wc_instance", "=", instance.id),
                ("ks_woo_payment_id", "=", payment_gateway_id)
            ], limit=1)
            auto_workflow = auto_workflow.ks_sale_workflow_id
        return auto_workflow

    def ks_prepare_export_json_data(self):
        if self.note==False:
            data = {
                'status': self.ks_woo_status,
        }
        else:
            data = {
                'customer_note': self.note,
                'status': self.ks_woo_status
            }
        order_lines = self._get_order_woo_lines(self.order_line)
        if order_lines:
            data.update({
                'line_items': order_lines
            })
        else:
            return False
        if self.partner_id:
            customer_data = self._ks_manage_customer(self.partner_id, self.partner_invoice_id, self.partner_shipping_id)
            if customer_data:
                data.update(customer_data)
            else:
                return False
        return data

    def _ks_manage_customer(self, customer, invoice, shipping):
        json_data = {}
        woo_customer = self.env["ks.woo.partner"].search([("ks_res_partner", "=", customer.id),
                                                          ("ks_wc_instance", "=", self.ks_wc_instance.id)])
        guest_customer = self.env.ref("ks_woocommerce.ks_woo_guest_customers")
        if woo_customer.ks_woo_partner_id:
            data = woo_customer.ks_prepare_export_json_data(invoice=invoice, shipping=shipping)
            if data.get('billing') and len(data.get('billing').get('email')) == 0:
                data['billing']['email'] = data.get('email')
            json_data = {
                'customer_id': woo_customer.ks_woo_partner_id,
                'billing': data['billing'] if data.get('billing') else '',
                'shipping': data['shipping'] if data.get('shipping') else '',
            }
        elif customer == guest_customer:
            data = woo_customer.ks_prepare_export_json_data(guest_customer)
            if data.get('billing') and len(data.get('billing').get('email')) == 0:
                data['billing']['email'] = data.get('email')
            json_data = {
                'customer_id': 0,
                'billing': data['billing'] if data.get('billing') else '',
                'shipping': data['shipping'] if data.get('shipping') else '',
            }
        else:
            layer_customer = self.env['ks.woo.partner'].create_woo_record(self.ks_wc_instance, customer,
                                                                          export_to_woo=True)
            if layer_customer:
                data = layer_customer.ks_prepare_export_json_data(invoice=invoice, shipping=shipping)
                if data.get('billing') and len(data.get('billing').get('email')) == 0:
                    data['billing']['email'] = data.get('email')
                json_data = {
                    'customer_id': layer_customer.ks_woo_partner_id,
                    'billing': data['billing'] if data.get('billing') else '',
                    'shipping': data['shipping'] if data.get('shipping') else '',
                }
            elif customer == guest_customer:
                data = layer_customer.ks_prepare_export_json_data(guest_customer)
                if data.get('billing') and len(data.get('billing').get('email')) == 0:
                    data['billing']['email'] = data.get('email')
                json_data = {
                    'customer_id': 0,
                    'billing': data['billing'] if data.get('billing') else '',
                    'shipping': data['shipping'] if data.get('shipping') else '',
                }
        return json_data

    def _prepare_invoice(self):
        invoice_vals = super(KsSaleOrderInherit, self)._prepare_invoice()
        if invoice_vals and self.ks_woo_order_id:
            invoice_vals.update({
                "ks_woo_order_id": self.id
            })
        return invoice_vals


class KsSaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    ks_woo_order_line_id = fields.Integer('WooCommerce Id', readonly=True)
    ks_discount_amount = fields.Float(string='Discount Amount', digits=(16, 4))

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'ks_discount_amount')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        super(KsSaleOrderLineInherit, self)._compute_amount()
        for line in self:
            if line.ks_discount_amount:
                price = line.price_unit - (
                    line.ks_discount_amount / line.product_uom_qty if line.ks_discount_amount else 0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id, partner=line.order_id.partner_shipping_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })
            if line.product_id.name == "Shipping Fees":
                price = line.price_unit
                taxes = line.tax_id.with_context({'woo_shipping': True}).compute_all(price, line.order_id.currency_id,
                                                                                     line.product_uom_qty,
                                                                                     product=line.product_id,
                                                                                     partner=line.order_id.partner_shipping_id,
                                                                                     handle_price_include=False)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })

    def _prepare_invoice_line(self, **optional_values):
        # Updating discount amount (in float) on invoice line
        res = super(KsSaleOrderLineInherit, self)._prepare_invoice_line(**optional_values)
        if self.ks_discount_amount and (self.qty_to_invoice * self.price_unit):
            discount = (self.ks_discount_amount / (self.qty_to_invoice * self.price_unit) if (
                                                                                                     self.qty_to_invoice * self.price_unit) > 0 else 1) * 100
            res.update({'discount': discount, 'ks_discount_amount_value': self.ks_discount_amount})
        return res


class KsBaseStockInventory(models.Model):
    _inherit = "stock.quant"

    for_woocommerce = fields.Boolean("WooCommerce Inventory Update")

    @api.model
    def ks_create_stock_inventory(self, product_data, location_id, auto_validate=False, queue_record=False):
        """
        This create the Inventory adjustment with the products and location
        :param product_data: list of dictionary {"product_id": 0, "product_qty": 0}
        :param location_id: stock.location() object
        :param auto_validate: If given the validate the adjustment created
        :return: stock.quant() if created
        """
        try:
            from datetime import datetime
            if product_data:
                inventories = self
                while product_data:
                    inventory_lines = product_data[:100]
                    inventory = self
                    inventory_name = 'product_inventory_%s' % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    new_products_values = []
                    for invent in inventory_lines:
                        p_id = self.env['product.product'].browse(invent['product_id']).id
                        if p_id:
                            inventory_values = {
                                'name': inventory_name,
                                'location_id': location_id.id if location_id else False,
                                'inventory_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'inventory_quantity': invent['product_qty'],
                                'prefill_counted_quantity': 'zero',
                                "company_id": location_id.company_id.id if location_id else self.env.company.id
                            }
                            self = self.env['stock.quant'].search(
                                [('product_id', '=', p_id), ('location_id', '=', location_id.id)])
                            if self:
                                self.write(inventory_values)
                                inventory += self
                                inventory.action_apply_inventory()
                            else:
                                inventory_values['product_id'] = p_id
                                inventory += self.create(inventory_values)
                                inventory.action_apply_inventory()

                    # inventory.ks_create_inventory_adjustment_lines(inventory_lines, location_id)
                    inventories += inventory
                    del product_data[:100]
                return inventories
            return False
        except Exception as e:
            # _logger.error(traceback.format_exc())
            if queue_record:
                queue_record.ks_update_failed_state()
            _logger.info(str(e))
            raise e



class KsStockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(KsStockQuant, self).create(vals_list)
        for record in records:
            if record.quantity and self.quantity != record.quantity:
                if record.quantity == 1.0:
                    record.update_stock_in_woo()
        return records

    def write(self, vals):
        qty_change = False
        if vals.get('quantity') and self.quantity != vals.get('quantity') and self.location_id.usage == 'internal':
            rec = super(KsStockQuant, self).write(vals)
            self.update_stock_in_woo()
            return rec
        else:
            rec = super(KsStockQuant, self).write(vals)
            return rec

    def update_stock_in_woo(self):
        stock_id = self._origin.id
        if stock_id:
            product_variant = self.product_id
            product_template = self.product_tmpl_id
            if product_template.ks_product_template:
                instance_id = product_template.ks_product_template.ks_wc_instance
                for rec in instance_id:
                    if rec.ks_auto_stock_sync_to_woo:
                        _logger.info("""Enqueuing Product""")
                        self.env['ks.woo.queue.jobs'].ks_create_product_stock_record_in_queue(rec,
                                                                                          records=product_template.ks_product_template)
                    else:
                        _logger.info("""Instance %s is not configured to Auto Stock Sync.""" % (
                        str(rec.display_name)))
            else:
                _logger.info("""Rejecting product variant %s 
                whose id : %s because it has not been synced on woo.""" % (
                    str(product_variant.display_name),
                    str(product_variant.id)))