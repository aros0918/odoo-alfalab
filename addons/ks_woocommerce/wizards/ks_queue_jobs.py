# -*- coding: utf-8 -*-

import json
import logging
import time
from odoo.exceptions import ValidationError
from odoo import models, fields

_logger = logging.getLogger(__name__)


class KsQueueManager(models.TransientModel):
    _name = 'ks.woo.queue.jobs'
    _description = 'Sync all operation in Queue'
    _rec_name = 'ks_name'
    _order = 'id desc'

    ks_model = fields.Selection([('product_template', 'Product Template'), ('product_product', 'Product Variants'),
                                 ('sale_order', 'Sale Order'), ('customer', 'Customer'), ('coupon', 'Coupon'),
                                 ('attribute', 'Attributes'), ('tag', 'Tags'), ('category', 'Category'),
                                 ('delivery', 'Delivery'), ('invoice', 'Invoices'), ('refund', 'Refunds'),
                                 ("stock", "stock"), ("tax", "Tax"), ('shipping', 'Shipping Method'),
                                 ('attribute_value', 'Attribute Value'), ('payment_gateway', 'Payment Gateway')],
                                string='Domain')
    ks_odoo_model = fields.Many2one("ir.model", string="Base Model")
    ks_layer_model = fields.Char(string="Layer Model")
    ks_name = fields.Char('Name')
    ks_operation = fields.Selection([('woo_to_odoo', 'Woo To Odoo'),
                                     ('odoo_to_woo', 'Odoo to Woo'),
                                     ('woo_to_wl', 'WooCommerce to Woo Layer'),
                                     ('wl_to_woo', 'Woo Layer to WooCommerce'),
                                     ('odoo_to_wl', 'Odoo to Woo Layer'),
                                     ('wl_to_odoo', 'Woo Layer to Odoo')],
                                    string="Operation Flow")
    ks_operation_type = fields.Selection([('create', 'Create'), ('update', 'Update')], "Operation Performed")
    ks_type = fields.Selection([('import', 'Import'), ('export', 'Export'), ('prepare', 'Prepare')],
                               string="Operation Type")
    state = fields.Selection([('new', 'New'), ('progress', 'In Progress'), ('done', 'Done'), ('failed', 'Failed')],
                             string='State', default='new')
    ks_woo_id = fields.Char('WooCommerce ID')
    ks_record_id = fields.Integer('Odoo ID')
    ks_wc_instance = fields.Many2one('ks.woo.connector.instance', 'Woo Instance')
    ks_data = fields.Text('WooCommerce Data')
    ks_images_with_products = fields.Boolean()
    ks_direct_export = fields.Boolean()
    ks_direct_update = fields.Boolean()
    ks_order_update = fields.Boolean(default=False)
    ks_product_config = fields.Text()

    def ks_process_queue_jobs(self):
        if not self.id:
            self = self.search([('state', 'in', ['new', 'failed', 'progress'])])
        for record in self:
            if record.ks_type == 'prepare':
                record.ks_update_progress_state()
                current_record = self.env[record.ks_odoo_model.model].search([('id', '=', record.ks_record_id)])
                if record.ks_operation_type == 'create':
                    try:
                        self.env[record.ks_layer_model].create_woo_record(record.ks_wc_instance,
                                                                          current_record, record.ks_direct_export,
                                                                          queue_record=record)
                        if record.state == 'progress':
                            record.ks_update_done_state()
                        self.env['ir.cron'].cron_initiate()
                        continue
                    except Exception as e:
                        self.env.cr.commit()
                        _logger.info(str(e))
                    self.env['ir.cron'].cron_initiate()

                if record.ks_operation_type == 'update':
                    try:
                        is_already_exported = self.env[record.ks_layer_model].check_if_already_prepared(
                            record.ks_wc_instance, current_record)
                        if is_already_exported:
                            self.env[record.ks_layer_model].update_woo_record(record.ks_wc_instance, current_record,
                                                                              record.ks_direct_update,
                                                                              queue_record=record)
                            if record.state == 'progress':
                                record.ks_update_done_state()
                            self.env['ir.cron'].cron_initiate()
                            continue
                        else:
                            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                                   status="failed",
                                                                                   instance=record.ks_wc_instance,
                                                                                   id=record.id,
                                                                                   message="Error in Prepare Update")

                    except Exception as e:
                        self.env.cr.commit()
                        _logger.info(str(e))
                    self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'category':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_wl':
                        _logger.info("Category syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        category_data = json.loads(record.ks_data)
                        category_record = self.env['ks.woo.product.category'].ks_manage_catgeory_import(
                            record.ks_wc_instance,
                            category_data,
                            queue_record=record
                        )
                        if category_record:
                            record.ks_record_id = category_record.id
                    elif record.ks_operation == 'wl_to_woo':
                        _logger.info("Category Export from Odoo to WooCommerce Initiated for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        category_record = self.env['ks.woo.product.category'].browse(record.ks_record_id)
                        category_response = category_record.ks_manage_category_export(queue_record=record)
                        if category_response.get("id"):
                            record.ks_woo_id = category_response.get("id")
                except Exception as e:
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))

                if record.state == 'progress':
                    record.ks_update_done_state()
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'customer':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_wl':
                        _logger.info("Customer syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        customer_data = json.loads(record.ks_data)
                        customer_record_exist = self.env['ks.woo.partner'].ks_manage_woo_customer_import(
                            record.ks_wc_instance,
                            customer_data,
                            queue_record=record)
                        if customer_record_exist:
                            record.ks_record_id = customer_record_exist.id
                    elif record.ks_operation == 'wl_to_woo':
                        _logger.info("Customer export from odoo to woocommerce starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        customer_record = self.env['ks.woo.partner'].browse(record.ks_record_id)
                        woo_customer_response = customer_record.ks_manage_woo_customer_export(queue_record=record)
                        if woo_customer_response.get("id"):
                            record.ks_woo_id = woo_customer_response.get("id")
                except Exception as e:
                    record.ks_update_failed_state()
                    _logger.info(str(e))
                    self.env.cr.commit()
                if record.state == 'progress':
                    record.ks_update_done_state()
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'tag':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_odoo':
                        _logger.info("Tags syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        tag_data = json.loads(record.ks_data)
                        tag_record_exist = self.env['ks.woo.product.tag'].search(
                            [('ks_wc_instance', '=', record.ks_wc_instance.id),
                             ('ks_woo_tag_id', '=', record.ks_woo_id)])
                        if tag_record_exist:
                            tag_record_exist.ks_woo_import_product_tag_update(tag_data, record.ks_wc_instance,
                                                                              queue_record=record)
                        else:
                            tag_record_exist = tag_record_exist.ks_manage_woo_product_tag_import(
                                record.ks_wc_instance, tag_data, queue_record=record)
                        if tag_record_exist:
                            record.ks_record_id = tag_record_exist.id
                    elif record.ks_operation == 'odoo_to_woo':
                        _logger.info("Tags export from odoo to woocommerce starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        tag_record = self.env['ks.woo.product.tag'].browse(record.ks_record_id)
                        if tag_record.ks_woo_tag_id:
                            tag_record.ks_update_tag_odoo_to_woo(queue_record=record)
                            if tag_record.ks_woo_tag_id:
                                record.ks_woo_id = tag_record.ks_woo_tag_id
                        else:
                            tag_record = tag_record.ks_create_tag_odoo_to_woo(queue_record=record)
                            if tag_record.get('id'):
                                record.ks_woo_id = tag_record.get('id')


                except Exception as e:
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))
                if record.state == 'progress':
                    record.ks_update_done_state()
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'payment_gateway':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_odoo':
                        _logger.info("Payment Gateway syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        pg_data = json.loads(record.ks_data)
                        pg_record_exist = self.env['ks.woo.payment.gateway'].search(
                            [('ks_wc_instance', '=', record.ks_wc_instance.id),
                             ('ks_woo_pg_id', '=', record.ks_woo_id)])
                        if pg_record_exist:
                            pg_record_exist.ks_woo_import_pg_update(pg_data, queue_record=record)
                        else:
                            pg_record_exist = pg_record_exist.ks_manage_woo_pg_import(record.ks_wc_instance, pg_data,
                                                                                      queue_record=record)
                        if pg_record_exist:
                            record.ks_record_id = pg_record_exist.id
                except Exception as e:
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))
                if record.state == 'progress':
                    record.ks_update_done_state()
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'attribute':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_wl':
                        _logger.info("Attribute syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        attribute_data = json.loads(record.ks_data)
                        attribute_record = self.env['ks.woo.product.attribute'].ks_manage_attribute_import(
                            record.ks_wc_instance,
                            attribute_data,
                            queue_record=record
                        )
                        if attribute_record:
                            record.ks_record_id = attribute_record.id
                    elif record.ks_operation == 'wl_to_woo':
                        _logger.info("Attribute Export from Odoo to WooCommerce Initiated for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name,
                                     record.ks_wc_instance.id)
                        attribute_record = self.env['ks.woo.product.attribute'].browse(record.ks_record_id)
                        attribute_response = attribute_record.ks_manage_attribute_export(queue_record=record)
                        if attribute_response.get("id"):
                            record.ks_woo_id = attribute_response.get("id")
                except Exception as e:
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))
                if record.state == 'progress':
                    record.ks_update_done_state()
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'product_template':
                record.ks_update_progress_state()
                _logger.info(" time " + str(time.time()))
                try:
                    if record.ks_operation == 'woo_to_wl':
                        _logger.info("Product syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        product_data = json.loads(record.ks_data)
                        if (product_data.get('type') == 'variable' and len(
                                product_data.get('variations')) == 0) or product_data.get('type') == 'variation':
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                               ks_model='product.template',
                                                                               ks_layer_model='ks.woo.product.template',
                                                                               ks_message="The Variable product does "
                                                                                          "not have variant data ",
                                                                               ks_status="failed",
                                                                               ks_type="product",
                                                                               ks_record_id=0,
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_woo_id=product_data.get(
                                                                                   "id", 0),
                                                                               ks_woo_instance=record.ks_wc_instance)
                            record.ks_update_failed_state()
                        else:
                            woo_product = self.env['ks.woo.product.template'].ks_manage_woo_product_template_import(
                                record.ks_wc_instance,
                                product_data,
                                queue_record=record)
                            if woo_product:
                                record.ks_record_id = woo_product.id
                    elif record.ks_operation == 'wl_to_woo':
                        _logger.info("Product export from odoo to woocommerce starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        product_record = self.env['ks.woo.product.template'].browse(record.ks_record_id)
                        product_config = json.loads(record.ks_product_config) if record.ks_product_config else False
                        product_record.ks_manage_woo_product_template_export(record.ks_wc_instance, queue_record=record,
                                                                             product_config=product_config)
                        if product_record.ks_woo_product_id:
                            record.ks_woo_id = product_record.ks_woo_product_id
                    if record.state == 'progress':
                        record.ks_update_done_state()
                    _logger.info(" time " + str(time.time()))
                    self.env['ir.cron'].cron_initiate()
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(
                        ks_operation_performed="create",
                        ks_model='ks.woo.product.template',
                        ks_layer_model='ks.woo.product.template',
                        ks_message="The product is already imported as an individual variant, can't proceed importing, with current configuration",
                        ks_status="failed",
                        ks_type="product",
                        ks_record_id=record.id,
                        ks_operation_flow="odoo_to_woo" if record.ks_operation == 'wl_to_woo' else 'woo_to_odoo',
                        ks_woo_id=0,
                        ks_woo_instance=record.ks_wc_instance)
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'tax':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_wl':
                        _logger.info("Tax syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        tax_data = json.loads(record.ks_data)
                        woo_tax = self.env['account.tax'].ks_get_tax_ids(
                            record.ks_wc_instance,
                            tax_data)
                        if woo_tax:
                            record.ks_record_id = woo_tax.id
                    if record.state == 'progress':
                        record.ks_update_done_state()
                    self.env['ir.cron'].cron_initiate()
                except Exception as e:
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'stock':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_odoo':
                        _logger.info("Stock syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        product_data = json.loads(record.ks_data)
                        if len(product_data) == 67:
                            if (product_data.get('type') == 'variable' and len(
                                    product_data.get('variations')) == 0) or product_data.get('type') == 'variation':
                                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                                   ks_model='stock.quant',
                                                                                   ks_layer_model='stock.quant',
                                                                                   ks_message="This stock  does "
                                                                                              "not have product data ",
                                                                                   ks_status="failed",
                                                                                   ks_type="stock",
                                                                                   ks_record_id=0,
                                                                                   ks_operation_flow="woo_to_odoo",
                                                                                   ks_woo_id=product_data.get(
                                                                                       "id", 0),
                                                                                   ks_woo_instance=record.ks_wc_instance)
                                record.ks_update_failed_state()
                            else:
                                product_data_non_filter = self.env[
                                    'ks.woo.product.template'].ks_get_product_data_for_stock_adjustment(
                                    product_data, record.ks_wc_instance)
                                valid_product_data = []
                                for rec in product_data_non_filter:
                                    if rec.get('product_id'):
                                        valid_product_data.append(rec)
                                inventory_adjustment_created = self.env['stock.quant'].ks_create_stock_inventory(
                                    valid_product_data, record.ks_wc_instance.ks_location_id,
                                    queue_record=record)
                                if inventory_adjustment_created:
                                    inventory_adjustment_created.for_woocommerce = True
                        else:
                            product_data_non_filter = self.env[
                                'ks.woo.product.template'].ks_get_product_data_for_stock_adjustment(
                                product_data, record.ks_wc_instance)
                            valid_product_data = []
                            for rec in product_data_non_filter:
                                if rec.get('product_id'):
                                    valid_product_data.append(rec)
                            inventory_adjustment_created = self.env['stock.quant'].ks_create_stock_inventory(
                                valid_product_data, record.ks_wc_instance.ks_location_id,
                                queue_record=record)
                            if inventory_adjustment_created:
                                inventory_adjustment_created.for_woocommerce = True
                    elif record.ks_operation == 'wl_to_woo':
                        _logger.info("Product Stock export from odoo to woocommerce starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        product_record = self.env['ks.woo.product.template'].browse(record.ks_record_id)
                        product_config = json.loads(record.ks_product_config) if record.ks_product_config else False
                        product_record.ks_manage_woo_product_template_export(record.ks_wc_instance, queue_record=record,
                                                                             product_config=product_config)
                        if product_record.ks_woo_product_id:
                            record.ks_woo_id = product_record.ks_woo_product_id

                    if record.state == 'progress':
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(
                            ks_operation_performed="create",
                            ks_model='stock.quant',
                            ks_layer_model='stock.quant',
                            ks_message="Inventory Operation Successful",
                            ks_status="success",
                            ks_type="stock",
                            ks_record_id=record.id,
                            ks_operation_flow="odoo_to_woo" if record.ks_operation == 'wl_to_woo' else 'woo_to_odoo',
                            ks_woo_id=0,
                            ks_woo_instance=record.ks_wc_instance)
                        record.ks_update_done_state()
                    self.env['ir.cron'].cron_initiate()
                except Exception as e:
                    record.ks_update_failed_state()
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(
                        ks_operation_performed="create",
                        ks_model='stock.quant',
                        ks_layer_model='stock.quant',
                        ks_message="Inventory Operation error %s" % str(e),
                        ks_status="failed",
                        ks_type="stock",
                        ks_record_id=record.id,
                        ks_operation_flow="odoo_to_woo" if record.ks_operation == 'wl_to_woo' else 'woo_to_odoo',
                        ks_woo_id=0,
                        ks_woo_instance=record.ks_wc_instance)
                    self.env.cr.commit()
                    _logger.info(str(e))
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'coupon':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_odoo':
                        _logger.info("Coupons syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        coupon_data = json.loads(record.ks_data)
                        coupon_record_exist = self.env['ks.woo.coupons'].search(
                            [('ks_wc_instance', '=', record.ks_wc_instance.id),
                             ('ks_woo_coupon_id', '=', record.ks_woo_id)])
                        if coupon_record_exist:
                            coupon_record_exist.ks_woo_import_coupon_update(coupon_data, queue_record=record)
                        else:
                            coupon_record_exist = coupon_record_exist.ks_woo_import_coupon_create(
                                coupon_data, record.ks_wc_instance, queue_record=record)
                        if coupon_record_exist:
                            record.ks_record_id = coupon_record_exist.id
                    elif record.ks_operation == 'odoo_to_woo':
                        _logger.info("Coupons export from odoo to woocommerce starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        coupon_record = self.env['ks.woo.coupons'].browse(record.ks_record_id)
                        coupon_response = None
                        if coupon_record.ks_woo_coupon_id:
                            coupon_record.ks_update_coupon_odoo_to_woo(queue_record=record)
                        else:
                            coupon_response = coupon_record.ks_create_coupon_odoo_to_woo(queue_record=record)
                        if coupon_record:
                            record.ks_woo_id = coupon_record.ks_woo_coupon_id
                        elif coupon_response:
                            record.ks_woo_id = coupon_response.get("id", 0)
                except Exception as e:
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))
                if record.state == 'progress':
                    record.ks_update_done_state()
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'sale_order':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_odoo':
                        _logger.info("Orders syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        order_data = json.loads(record.ks_data)
                        order_record_exist = self.env['sale.order'].search(
                            [('ks_wc_instance', '=', record.ks_wc_instance.id),
                             ('ks_woo_order_id', '=', record.ks_woo_id)])
                        if order_record_exist:
                            order_record_exist.ks_woo_import_order_update(order_data, queue_record=record,
                                                                          update=record.ks_order_update)
                        else:
                            order_record_exist = order_record_exist.ks_woo_import_order_create(
                                order_data, record.ks_wc_instance, queue_record=record)
                        if order_record_exist:
                            record.ks_record_id = order_record_exist.id

                    if record.ks_operation == 'odoo_to_woo':
                        _logger.info("Orders syncing from Odoo to Woocommerce starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        sale_order_record = self.env['sale.order'].browse(record.ks_record_id)
                        response = sale_order_record.ks_export_order_to_woo(queue_record=record)
                        if response == False:
                            record.ks_update_failed_state()
                        else:
                            record.ks_woo_id = response.get("id", 0)
                except Exception as e:
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))
                if record.state == 'progress':
                    record.ks_update_done_state()
                self.env['ir.cron'].cron_initiate()

            if record.ks_model == 'shipping':
                record.ks_update_progress_state()
                try:
                    if record.ks_operation == 'woo_to_odoo':
                        _logger.info("Shipping Method syncing from woocommerce to odoo starts for instance [%s -(%s)]",
                                     record.ks_wc_instance.ks_instance_name, record.ks_wc_instance.id)
                        shipping_data = json.loads(record.ks_data)
                        shipping_record_exist = self.env['ks.woo.delivery.carrier'].ks_woo_import_shipping_method(
                            shipping_data, record.ks_wc_instance, queue_record=record)
                        if shipping_record_exist:
                            record.ks_record_id = shipping_record_exist.id
                except Exception as e:
                    record.ks_update_failed_state()
                    self.env.cr.commit()
                    _logger.info(str(e))
                if record.state == 'progress':
                    record.ks_update_done_state()
                self.env['ir.cron'].cron_initiate()

        self += self.search([('state', 'in', ['new', 'failed', 'progress'])])

    def get_model(self, instance_model):
        if instance_model == "ks.woo.partner":
            return "customer"
        elif instance_model == "ks.woo.product.variant":
            return "product_product"
        elif instance_model == "ks.woo.product.template":
            return "product_template"
        elif instance_model == 'ks.woo.product.tag':
            return "tag"
        elif instance_model == 'ks.woo.product.category':
            return "category"
        elif instance_model == 'ks.woo.product.attribute':
            return "attribute"
        elif instance_model == "ks.woo.pro.attr.value":
            return "attribute_value"
        elif instance_model == 'ks.woo.payment.gateway':
            return "payment_gateway"
        else:
            return "coupon"

    def ks_create_prepare_record_in_queue(self, instance, instance_model, active_model, record_id, type,
                                          update_to_woo=False, export_to_woo=False):
        current_record = self.env[active_model].browse(record_id)
        odoo_model = self.env['ir.model'].search([('model', '=', current_record._name)])
        model_involved = self.get_model(instance_model)
        record_data = {
            'ks_name': current_record.display_name,
            'ks_wc_instance': instance.id,
            'ks_record_id': record_id,
            'ks_odoo_model': odoo_model.id,
            'ks_type': 'prepare',
            'ks_operation_type': type,
            'ks_operation': 'odoo_to_wl',
            "ks_direct_update": update_to_woo,
            "ks_direct_export": export_to_woo,
            'ks_layer_model': instance_model,
            'ks_model': model_involved
        }
        try:
            self.create(record_data)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_model=active_model,
                                                               ks_woo_instance=instance,
                                                               ks_record_id=record_id,
                                                               ks_message='Prepare operation to queue jobs added Successfully',
                                                               ks_woo_id=0,
                                                               ks_operation_flow='odoo_to_woo',
                                                               ks_status="success",
                                                               ks_type="system_status")
            self.env['ir.cron'].cron_initiate()
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_model=active_model,
                                                               ks_woo_instance=instance,
                                                               ks_record_id=record_id,
                                                               ks_message="Prepare operation to queue jobs Failed due to %s" % e,
                                                               ks_woo_id=0,
                                                               ks_operation_flow='odoo_to_woo',
                                                               ks_status="Failed",
                                                               ks_type="system_status")

    def ks_create_customer_record_in_queue(self, instance=False, data=False, records=False, woo=False):
        vals = []
        if data:
            for record in data:
                ks_woo_id = record.get('id')
                customer_data = {
                    'ks_name': record.get('first_name'),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_wl',
                    'ks_model': 'customer',
                    'ks_woo_id': ks_woo_id
                }
                vals.append(customer_data)
        elif records:
            for each_record in records:
                customer_data = {
                    'ks_name': each_record.display_name,
                    'ks_model': 'customer',
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_partner_id,
                    'ks_operation': 'wl_to_woo',
                    'state': 'new',
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_type': 'export'
                }
                vals.append(customer_data)
        if vals:
            self.create(vals)
            if not woo:
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                                   ks_type='customer',
                                                                   ks_woo_instance=instance,
                                                                   ks_record_id=0,
                                                                   ks_message="Customer Sync operation to queue jobs added Successfully",
                                                                   ks_woo_id=0,
                                                                   ks_operation_flow='woo_to_odoo',
                                                                   ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='customer',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Customer failed to Enqueue. Verify the appropriate configuration is enabled",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_taxes_record_in_queue(self, instance=False, data=False, records=False):
        vals = []
        if data:
            for record in data:
                ks_woo_id = record.get('id')
                tax_data = {
                    'ks_name': record.get('name'),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_wl',
                    'ks_model': 'tax',
                    'ks_woo_id': ks_woo_id
                }
                vals.append(tax_data)
        elif records:
            for each_record in records:
                tax_data = {
                    'ks_name': each_record.display_name,
                    'ks_model': 'tax',
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_id,
                    'ks_operation': 'wl_to_woo',
                    'state': 'new',
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_type': 'export'
                }
                vals.append(tax_data)
        if vals:
            self.create(vals)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='tax',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Tax Sync operation to queue jobs added Successfully",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='tax',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Tax failed to Enqueue. Verify the appropriate configuration is enabled",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_product_record_in_queue(self, instance=False, data=False, records=False, product_config=False,
                                          woo=False):
        vals = []
        if data:
            if instance.ks_sync_unpublished_product:
                for record in data:
                    if record.get('status') == 'pending' or record.get('status') == 'private' or record.get(
                            'status') == 'publish' or record.get('status') == 'draft':
                        ks_woo_id = record.get('id')
                        product_data = {
                            'ks_name': record.get('name'),
                            'ks_wc_instance': instance.id,
                            'ks_data': json.dumps(record),
                            'ks_type': 'import',
                            'state': 'new',
                            'ks_operation': 'woo_to_wl',
                            'ks_model': 'product_template',
                            'ks_woo_id': ks_woo_id
                        }
                        vals.append(product_data)
            else:
                for record in data:
                    if record.get('status') == 'pending' or record.get('status') == 'publish' or record.get(
                            'status') == 'private':
                        ks_woo_id = record.get('id')
                        product_data = {
                            'ks_name': record.get('name'),
                            'ks_wc_instance': instance.id,
                            'ks_data': json.dumps(record),
                            'ks_type': 'import',
                            'state': 'new',
                            'ks_operation': 'woo_to_wl',
                            'ks_model': 'product_template',
                            'ks_woo_id': ks_woo_id
                        }
                        vals.append(product_data)
        elif records:
            for each_record in records:
                customer_data = {
                    'ks_name': each_record.display_name or ' ',
                    'ks_model': 'product_template',
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_product_id,
                    'ks_operation': 'wl_to_woo',
                    'state': 'new',
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_type': 'export'
                }
                if product_config:
                    customer_data.update(
                        {
                            'ks_product_config': json.dumps(product_config)
                        }
                    )
                vals.append(customer_data)
        if vals:
            self.create(vals)
            if not woo:
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                                   ks_type='product',
                                                                   ks_woo_instance=instance,
                                                                   ks_record_id=0,
                                                                   ks_message="Product Sync operation to queue jobs added Successfully",
                                                                   ks_woo_id=0,
                                                                   ks_operation_flow='woo_to_odoo',
                                                                   ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='product',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Product failed to Enqueue. Verify the appropriate configuration is enabled",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_product_stock_record_in_queue(self, instance=False, records=False, product_config=False):
        vals = []
        if records:
            for each_record in records:
                prod_stock_data = {
                    'ks_name': each_record.display_name,
                    'ks_model': 'stock',
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_product_id,
                    'ks_operation': 'wl_to_woo',
                    'state': 'new',
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_type': 'export'
                }
                if product_config:
                    prod_stock_data.update(
                        {
                            'ks_product_config': json.dumps(product_config)
                        }
                    )
                vals.append(prod_stock_data)
        if vals:
            self.create(vals)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='stock',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Product Stocks Sync operation to queue jobs added Successfully",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='stock',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Product Stocks failed to Enqueue. Verify the appropriate configuration is enabled",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_shipping_record_in_queue(self, instance=False, data=False):
        vals = []
        if data:
            for record in data:
                woo_id = record.get('id')
                shipping_data = {
                    'ks_name': record.get('name') if record.get('name') else record.get('id'),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_odoo',
                    'ks_model': 'shipping',
                    'ks_woo_id': woo_id
                }
                vals.append(shipping_data)
        if vals:
            self.create(vals)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='shipping',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Shipping Methods enqueue operation to queue jobs added Successfully",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='shipping',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Shipping Methods failed to Enqueue. Verify the appropriate configuration is enabled",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_attribute_record_in_queue(self, instance=False, data=False, records=False):
        vals = []
        if data:
            for record in data:
                woo_id = record.get('id')
                attribute_data = {
                    'ks_name': record.get('name'),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_wl',
                    'ks_model': 'attribute',
                    'ks_woo_id': woo_id
                }
                vals.append(attribute_data)

        if records:
            for each_record in records:
                attribute_data = {
                    'ks_name': each_record.display_name,
                    'ks_model': 'attribute',
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_attribute_id,
                    'ks_operation': 'wl_to_woo',
                    'state': 'new',
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_type': 'export'
                }
                vals.append(attribute_data)
        if vals:
            self.create(vals)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='attribute',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Attributes enqueue operation to queue jobs added Successfully",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='attribute',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Attributes failed to Enqueue. Verify the appropriate configuration is enabled",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_category_record_in_queue(self, instance=False, data=False, records=False):
        vals = []
        if data:
            for record in data:
                woo_id = record.get("id")
                category_data = {
                    'ks_name': record.get('name'),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_wl',
                    'ks_model': 'category',
                    'ks_woo_id': woo_id
                }
                vals.append(category_data)
        if records:
            for each_record in records:
                category_data = {
                    'ks_name': each_record.display_name,
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_record_id': each_record.id,
                    'ks_type': 'export',
                    'state': 'new',
                    'ks_operation': 'wl_to_woo',
                    'ks_model': 'category',
                    'ks_woo_id': int(each_record.ks_woo_category_id)
                }
                vals.append(category_data)
        if vals:
            self.create(vals)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='category',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Category Enqueue operation to queue jobs added Successfully",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='category',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message="Category failed to Enqueue. Verify the appropriate configuration is enabled",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_import_stock_woocommerce_in_queue(self, instance, data):
        stock_data = {
            'ks_name': 'Inventory Adjustment ',
            'ks_wc_instance': instance.id,
            'ks_data': json.dumps(data),
            'ks_type': 'import',
            'state': 'new',
            'ks_operation': 'woo_to_odoo',
            'ks_model': 'stock',
            'ks_woo_id': 0
        }
        self.create(stock_data)
        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                           ks_type='stock',
                                                           ks_woo_instance=instance,
                                                           ks_record_id=0,
                                                           ks_message='stock import operation to queue jobs added Successfully',
                                                           ks_woo_id=0,
                                                           ks_operation_flow='woo_to_odoo',
                                                           ks_status="success")

    def ks_create_tag_record_in_queue(self, instance=False, data=False, records=False):
        vals = []
        if data:
            for record in data:
                woo_id = record.get("id")
                tag_data = {
                    'ks_name': record.get('name'),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_odoo',
                    'ks_model': 'tag',
                    'ks_woo_id': woo_id
                }
                vals.append(tag_data)
        if records:
            for each_record in records:
                tag_data = {
                    'ks_name': each_record.display_name,
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_record_id': each_record.id,
                    'ks_type': 'export',
                    'state': 'new',
                    'ks_operation': 'odoo_to_woo',
                    'ks_model': 'tag',
                    'ks_woo_id': each_record.ks_woo_tag_id
                }
                vals.append(tag_data)
        if vals:
            self.create(vals)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='tags',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='Tags Enqueue operation to queue jobs added Successfully',
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='tags',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='Tags failed to Enqueue. Verify the appropriate configuration is enabled',
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_coupon_record_in_queue(self, instance=False, data=False, records=False, woo=False):
        vals = []
        if data:
            for record in data:
                woo_id = record.get("id")
                tag_data = {
                    'ks_name': record.get('code'),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_odoo',
                    'ks_model': 'coupon',
                    'ks_woo_id': woo_id
                }
                vals.append(tag_data)
        if records:
            for each_record in records:
                tag_data = {
                    'ks_name': each_record.ks_coupon_code,
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_record_id': each_record.id,
                    'ks_type': 'export',
                    'state': 'new',
                    'ks_operation': 'odoo_to_woo',
                    'ks_model': 'coupon',
                    'ks_woo_id': each_record.ks_woo_coupon_id
                }
                vals.append(tag_data)
        if vals:
            self.create(vals)
            if not woo:
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                                   ks_type='coupon',
                                                                   ks_woo_instance=instance,
                                                                   ks_record_id=0,
                                                                   ks_message='Coupons Enqueue operation to queue jobs added Successfully',
                                                                   ks_woo_id=0,
                                                                   ks_operation_flow='woo_to_odoo',
                                                                   ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='coupon',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='Coupons failed to Enqueue. Verify the appropriate configuration is enabled',
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_order_record_in_queue(self, instance=False, data=False, records=False, woo=False, update=False):
        vals = []
        if data:
            for record in data:
                woo_id = record.get("id")
                order_data = {
                    'ks_name': "Sale Order #" + str(woo_id),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_odoo',
                    'ks_model': 'sale_order',
                    'ks_woo_id': woo_id
                }
                if update:
                    order_data.update({
                        'ks_order_update': True,
                    })
                vals.append(order_data)
        if records:
            for each_record in records:
                order_data = {
                    'ks_name': each_record.display_name,
                    'ks_wc_instance': each_record.ks_wc_instance.id,
                    'ks_record_id': each_record.id,
                    'ks_type': 'export',
                    'state': 'new',
                    'ks_operation': 'odoo_to_woo',
                    'ks_model': 'sale_order',
                    'ks_woo_id': each_record.ks_woo_order_id
                }
                vals.append(order_data)
        if vals:
            self.create(vals)
            if not woo:
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                                   ks_type='order',
                                                                   ks_woo_instance=instance,
                                                                   ks_record_id=0,
                                                                   ks_message='Orders Enqueue operation to queue jobs added Successfully',
                                                                   ks_woo_id=0,
                                                                   ks_operation_flow='woo_to_odoo',
                                                                   ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='order',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='Orders failed to Enqueue. Verify the appropriate configuration is enabled',
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_create_pg_record_in_queue(self, instance, data):
        vals = []
        if data:
            for record in data:
                woo_id = record.get("id")
                pg_data = {
                    'ks_name': record.get('title'),
                    'ks_wc_instance': instance.id,
                    'ks_data': json.dumps(record),
                    'ks_type': 'import',
                    'state': 'new',
                    'ks_operation': 'woo_to_odoo',
                    'ks_model': 'payment_gateway',
                    'ks_woo_id': woo_id
                }
                vals.append(pg_data)
        if vals:
            self.create(vals)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='payment_gateway',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='Payment Gateway Enqueue operation to queue jobs added Successfully',
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="success")
            self.env['ir.cron'].cron_initiate()
        else:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_type='payment_gateway',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='Payment Gateway failed to Enqueue. Verify the appropriate configuration is enabled',
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed")

    def ks_update_failed_state(self):
        self.state = 'failed'
        self.env.cr.commit()

    def ks_update_done_state(self):
        self.state = 'done'
        self.env.cr.commit()

    def ks_update_progress_state(self):
        self.state = 'progress'
        self.env.cr.commit()
