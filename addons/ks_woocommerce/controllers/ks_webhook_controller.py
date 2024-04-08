# -*- coding: utf-8 -*-

import json
import base64
import logging

from odoo import http, SUPERUSER_ID
# from odoo.http import Root
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class KsWooWebhookHandler(http.Controller):
    @http.route(['/woo_hook/<string:db>/<string:uid>/<int:woo_instance_id>/customer/create'], auth='none', csrf=False, methods=['POST'])
    def create_customer_webhook(self, db, woo_instance_id, uid, **post):
        if request.env['ks.woo.connector.instance'].sudo().search([('ks_instance_state', 'in', ['active'])]):
            try:
                encoded_db = db.strip()
                decoded_db = base64.urlsafe_b64decode(encoded_db)
                request.session.db = str(decoded_db, "utf-8")
                woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                      limit=1)
                data = request.httprequest.data
                data_json = data.decode('utf8').replace("'", '"')
                data_j = json.loads(data_json)
                request.env['ks.woo.webhook.logger'].ks_create_webhook_log_param(ks_operation_performed="customer_create",
                                                                                 ks_status="draft",
                                                                                 ks_type="webhook",
                                                                                 ks_woo_instance=woo_instance,
                                                                                 ks_woo_id=data_j['id'],
                                                                                 ks_message='Create Customer Webhook Triggered Successfully')
                if uid:
                    request.session.uid = int(uid)
                    request.env.user = request.env['res.users'].browse(int(uid))
                    request.env.uid = int(uid)
                if data_j:
                    self._ks_check_user()
                    if woo_instance_id:
                        if woo_instance and data_j:
                            request.env.company = woo_instance.ks_company_id
                            request.env.companies = woo_instance.ks_company_id
                            request.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance=woo_instance, woo=True,
                                                                                         data=[data_j])
                            _logger.info('Customer enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , woo_instance.ks_instance_name, woo_instance.id)
                            return 'ok'
                return 'ok'
            except Exception as e:
                _logger.info("Create of customer failed with exception through webhook failed "+str(e))
                return request.not_found()
        else:
            _logger.info('Order create through webhook failed because instance is not activated.')

    @http.route(['/woo_hook/<string:db>/<string:uid>/<int:woo_instance_id>/customer/update'], auth='none', csrf=False, methods=['POST'])
    def update_customer_webhook(self, woo_instance_id, db, uid, **post):
        if request.env['ks.woo.connector.instance'].sudo().search([('ks_instance_state', 'in', ['active'])]):
            try:
                encoded_db = db.strip()
                decoded_db = base64.urlsafe_b64decode(encoded_db)
                request.session.db = str(decoded_db, "utf-8")
                woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                      limit=1)
                data = request.httprequest.data
                data_json = data.decode('utf8').replace("'", '"')
                data_j = json.loads(data_json)
                request.env['ks.woo.webhook.logger'].ks_create_webhook_log_param(ks_operation_performed="customer_update",
                                                                                 ks_status="draft",
                                                                                 ks_type="webhook",
                                                                                 ks_woo_instance=woo_instance,
                                                                                 ks_woo_id=data_j['id'],
                                                                                 ks_message='Customer Update Webhook Triggered Successfully')
                if uid:
                    request.session.uid = int(uid)
                    request.env.user = request.env['res.users'].browse(int(uid))
                    request.env.uid = int(uid)
                if data_j:
                    self._ks_check_user()
                    if woo_instance_id:
                        woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                              limit=1)
                        if woo_instance and data_j:
                            request.env.company = woo_instance.ks_company_id
                            request.env.companies = woo_instance.ks_company_id
                            request.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance=woo_instance, woo=True,
                                                                                                data=[data_j])
                            _logger.info('Customer enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , woo_instance.ks_instance_name, woo_instance.id)
                            return 'ok'
                return 'ok'
            except Exception as e:
                _logger.info("Update of customer failed through webhook failed "+str(e))
                return Response("The requested URL was not found on the server.", status=404)
        else:
            _logger.info('Order create through webhook failed because instance is not activated.')


    @http.route(['/woo_hook/<string:db>/<string:uid>/<int:woo_instance_id>/coupon/create'], auth='none', csrf=False, methods=['POST'])
    def create_coupon_webhook(self, woo_instance_id, db, uid, **post):
        if request.env['ks.woo.connector.instance'].sudo().search([('ks_instance_state', 'in', ['active'])]):
            try:
                encoded_db = db.strip()
                decoded_db = base64.urlsafe_b64decode(encoded_db)
                request.session.db = str(decoded_db, "utf-8")
                woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                      limit=1)
                data = request.httprequest.data
                data_json = data.decode('utf8').replace("'", '"')
                data_j = json.loads(data_json)
                request.env['ks.woo.webhook.logger'].ks_create_webhook_log_param(ks_operation_performed="coupon_create",
                                                                                 ks_status="draft",
                                                                                 ks_type="webhook",
                                                                                 ks_woo_instance=woo_instance,
                                                                                 ks_woo_id=data_j['id'],
                                                                                 ks_message='Coupon Create Webhook Triggered Successfully')
                if uid:
                    request.session.uid = int(uid)
                    request.env.user = request.env['res.users'].browse(int(uid))
                    request.env.uid = int(uid)
                if data_j:
                    self._ks_check_user()
                    if woo_instance_id:
                        if woo_instance and data_j:
                            request.env.company = woo_instance.ks_company_id
                            request.env.companies = woo_instance.ks_company_id
                            request.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=woo_instance, woo=True,
                                                                                                   data=[data_j])
                            _logger.info('Coupon enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , woo_instance.ks_instance_name, woo_instance.id)
                return 'ok'
            except Exception as e:
                _logger.info("Create of coupon failed through webhook failed "+str(e))
                return Response("The requested URL was not found on the server.", status=404)
        else:
            _logger.info('Order create through webhook failed because instance is not activated.')


    @http.route(['/woo_hook/<string:db>/<string:uid>/<int:woo_instance_id>/coupon/update'], auth='none', csrf=False, methods=['POST'])
    def update_coupon_webhook(self, woo_instance_id, db, uid, **post):
        if request.env['ks.woo.connector.instance'].sudo().search([('ks_instance_state', 'in', ['active'])]):
            try:
                encoded_db = db.strip()
                decoded_db = base64.urlsafe_b64decode(encoded_db)
                request.session.db = str(decoded_db, "utf-8")
                woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                      limit=1)
                data = request.httprequest.data
                data_json = data.decode('utf8').replace("'", '"')
                data_j = json.loads(data_json)
                request.env['ks.woo.webhook.logger'].ks_create_webhook_log_param(ks_operation_performed="coupon_update",
                                                                                 ks_status="draft",
                                                                                 ks_type="webhook",
                                                                                 ks_woo_instance=woo_instance,
                                                                                 ks_woo_id=data_j['id'],
                                                                                 ks_message='Coupon Update Webhook Triggered Successfully')
                if uid:
                    request.session.uid = int(uid)
                    request.env.user = request.env['res.users'].browse(int(uid))
                    request.env.uid = int(uid)
                if data_j:
                    self._ks_check_user()
                    if woo_instance_id:
                        if woo_instance and data_j:
                            request.env.company = woo_instance.ks_company_id
                            request.env.companies = woo_instance.ks_company_id
                            request.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=woo_instance, woo=True,
                                                                                              data=[data_j])
                            _logger.info('Coupon enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , woo_instance.ks_instance_name, woo_instance.id)
                return 'ok'
            except Exception as e:
                _logger.info("Update of coupon failed through webhook failed "+str(e))
                return Response("The requested URL was not found on the server.", status=404)
        else:
            _logger.info('Order create through webhook failed because instance is not activated.')


    @http.route(['/woo_hook/<string:db>/<string:uid>/<int:woo_instance_id>/product/create'], auth='none', csrf=False, methods=['POST'])
    def create_product_webhook(self, woo_instance_id, db, uid, **post):
        if request.env['ks.woo.connector.instance'].sudo().search([('ks_instance_state', 'in', ['active'])]):
            try:
                encoded_db = db.strip()
                decoded_db = base64.urlsafe_b64decode(encoded_db)
                request.session.db = str(decoded_db, "utf-8")
                woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                      limit=1)
                data = request.httprequest.data
                data_json = data.decode('utf8').replace("'", '"')
                data_j = json.loads(data_json)
                request.env['ks.woo.webhook.logger'].ks_create_webhook_log_param(ks_operation_performed="product_create",
                                                                             ks_status="draft",
                                                                             ks_type="webhook",
                                                                             ks_woo_instance=woo_instance,
                                                                             ks_woo_id=data_j['id'],
                                                                             ks_message='Product Create Webhook Triggered Successfully')

                if uid:
                    request.session.uid = int(uid)
                    request.env.user = request.env['res.users'].browse(int(uid))
                    request.env.uid = int(uid)

                if data_j:
                    self._ks_check_user()
                    if woo_instance_id:
                        if woo_instance and data_j:
                            request.env.company = woo_instance.ks_company_id
                            request.env.companies = woo_instance.ks_company_id
                            if woo_instance.ks_woo_auto_stock_import:
                                request.env['ks.woo.queue.jobs'].sudo().ks_import_stock_woocommerce_in_queue(
                                    woo_instance, data_j)
                            request.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=woo_instance, woo=True,
                                                                                            data=[data_j])
                            _logger.info('Product enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , woo_instance.ks_instance_name, woo_instance.id)
                return 'ok'
            except Exception as e:
                _logger.info("Create of product failed through webhook failed "+str(e))
                return request.not_found()
        else:
            _logger.info('Order create through webhook failed because instance is not activated.')


    @http.route(['/woo_hook/<string:db>/<string:uid>/<int:woo_instance_id>/product/update'], auth='none', csrf=False, methods=['POST'])
    def update_product_webhook(self, woo_instance_id, db, uid, **post):
        if request.env['ks.woo.connector.instance'].sudo().search([('ks_instance_state', 'in', ['active'])]):
            try:
                encoded_db = db.strip()
                decoded_db = base64.urlsafe_b64decode(encoded_db)
                request.session.db = str(decoded_db, "utf-8")
                woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                      limit=1)
                data = request.httprequest.data
                data_json = data.decode('utf8').replace("'", '"')
                data_j = json.loads(data_json)
                request.env['ks.woo.webhook.logger'].ks_create_webhook_log_param(ks_operation_performed="product_update",
                                                                                 ks_status="draft",
                                                                                 ks_type="webhook",
                                                                                 ks_woo_instance=woo_instance,
                                                                                 ks_woo_id=data_j['id'],
                                                                                 ks_message='Product Update Webhook Triggered Successfully')
                if uid:
                    request.session.uid = int(uid)
                    request.env.user = request.env['res.users'].browse(int(uid))
                    request.env.uid = int(uid)
                if data_j:
                    self._ks_check_user()
                    if woo_instance_id:
                        if woo_instance and data:
                            request.env.company = woo_instance.ks_company_id
                            request.env.companies = woo_instance.ks_company_id
                            if woo_instance.ks_woo_auto_stock_import:
                                request.env['ks.woo.queue.jobs'].sudo().ks_import_stock_woocommerce_in_queue(
                                    woo_instance, data_j)
                            request.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=woo_instance, woo=True,
                                                                                               data=[data_j])
                            _logger.info('Product enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , woo_instance.ks_instance_name, woo_instance.id)
                return 'ok'
            except Exception as e:
                _logger.info("Update of product failed through webhook failed "+str(e))
                return request.not_found()
        else:
            _logger.info('Order create through webhook failed because instance is not activated.')


    @http.route(['/woo_hook/<string:db>/<string:uid>/<int:woo_instance_id>/order/create'], auth='none', csrf=False, methods=['POST'])
    def create_order_webhook(self, woo_instance_id, db, uid, **post):
        if request.env['ks.woo.connector.instance'].sudo().search([('ks_instance_state', 'in', ['active'])]):
            try:
                encoded_db = db.strip()
                decoded_db = base64.urlsafe_b64decode(encoded_db)
                request.session.db = str(decoded_db, "utf-8")
                woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                  limit=1)
                data = request.httprequest.data
                data_json = data.decode('utf8').replace("'", '"')
                data_j = json.loads(data_json)
                request.env['ks.woo.webhook.logger'].ks_create_webhook_log_param(ks_operation_performed="order_create",
                                                                             ks_status="draft",
                                                                             ks_type="webhook",
                                                                             ks_woo_instance=woo_instance,
                                                                             ks_woo_id=data_j['id'],
                                                                             ks_message='Order Create Webhook Triggered Successfully')
                if uid:
                    request.session.uid = int(uid)
                    request.env.user = request.env['res.users'].browse(int(uid))
                    request.env.uid = int(uid)

                if data_j:
                    self._ks_check_user()
                    if woo_instance_id:
                        if woo_instance and data_j:
                            request.env.company = woo_instance.ks_company_id
                            request.env.companies = woo_instance.ks_company_id
                            ks_woo_sync_status = woo_instance.ks_order_status.mapped('status')
                            if data_j.get('status', False) in ks_woo_sync_status:
                                request.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=woo_instance,
                                                                                              data=[data_j])
                                _logger.info('Order enqueue start For WooCommerce Instance [%s -(%s)]'
                                     , woo_instance.ks_instance_name, woo_instance.id)
                            _logger.info('Order do not map to the Order Status %s for %s'
                                     , ks_woo_sync_status, woo_instance.ks_instance_name)
                    return 'ok'
            except Exception as e:
                _logger.info("Create of order failed through webhook failed "+str(e))
                return request.not_found()
        else:
            _logger.info('Order create through webhook failed because instance is not activated.')
    @http.route(['/woo_hook/<string:db>/<string:uid>/<int:woo_instance_id>/order/update'], auth='none', csrf=False, methods=['POST'])
    def update_order_webhook(self, woo_instance_id, db, uid, **post):
        if request.env['ks.woo.connector.instance'].sudo().search([('ks_instance_state', 'in', ['active'])]):
            try:
                encoded_db = db.strip()
                decoded_db = base64.urlsafe_b64decode(encoded_db)
                request.session.db = str(decoded_db, "utf-8")
                woo_instance = request.env['ks.woo.connector.instance'].sudo().search([('id', '=', woo_instance_id)],
                                                                                  limit=1)
                data = request.httprequest.data
                data_json = data.decode('utf8').replace("'", '"')
                data_j = json.loads(data_json)
                request.env['ks.woo.webhook.logger'].ks_create_webhook_log_param(ks_operation_performed="order_update",
                                                                                ks_status="draft",
                                                                                ks_type="webhook",
                                                                                ks_woo_instance=woo_instance,
                                                                                ks_woo_id=data_j['id'],
                                                                                ks_message='Order Update Webhook Triggered Successfully')
                if uid:
                    request.session.uid = int(uid)
                    request.env.user = request.env['res.users'].browse(int(uid))
                    request.env.uid = int(uid)
                if data_j:
                    self._ks_check_user()
                    if woo_instance_id:
                        if woo_instance and data_j:
                            request.env.company = woo_instance.ks_company_id
                            request.env.companies = woo_instance.ks_company_id
                            ks_woo_sync_status = woo_instance.ks_order_status.mapped('status')
                            if data_j.get('status', False) in ks_woo_sync_status:
                                order_record_exist = request.env['sale.order'].sudo().search(
                                    [('ks_wc_instance', '=', woo_instance.id),
                                        ('ks_woo_order_id', '=', data_j.get("id"))], limit=1)
                                if order_record_exist:
                                    request.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=woo_instance,
                                                                                                 data=[data_j])
                                    _logger.info('Order enqueue start For WooCommerce Instance [%s -(%s)]'
                                        , woo_instance.ks_instance_name, woo_instance.id)
                            else:
                                _logger.info('Order do not map to the Order Status %s for %s'
                                            , ks_woo_sync_status, woo_instance.ks_instance_name)
                    return 'ok'
            except Exception as e:
                _logger.info("Update of order through webhook failed "+str(e))
                return request.not_found()
        else:
            _logger.info('Order Update through webhook failed because instance is not activated.')


    def _ks_check_user(self):
        if request.env.user.has_group('base.group_public'):
            request.env.user = request.env['res.users'].browse(SUPERUSER_ID)
            request.env.uid = SUPERUSER_ID
        return request.env.user


# old_get_request = Root.get_request


def get_request(self, httprequest):
    is_json = httprequest.args.get('jsonp') or httprequest.mimetype in ("application/json", "application/json-rpc")
    httprequest.data = {}
    woo_hook_path = ks_match_the_url_path(httprequest.path)
    if woo_hook_path and is_json:
        request = httprequest.get_data().decode(httprequest.charset)
        httprequest.data = json.loads(request)
        return HttpRequest(httprequest)
    return old_get_request(self, httprequest)


# Root.get_request = get_request


def ks_match_the_url_path(path):
    if path:
        path_list = path.split('/')
        if path_list[1] == 'woo_hook' and path_list[5] in ['customer', 'coupon', 'product',
                                                                                 'order'] and path_list[6] in ['create',
                                                                                                               'update']:
            return True
        else:
            return False
