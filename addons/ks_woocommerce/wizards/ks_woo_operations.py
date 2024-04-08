# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from requests.exceptions import ConnectionError

_logger = logging.getLogger(__name__)

class KsWooInstanceOperation(models.TransientModel):
    _name = "ks.woo.instance.operations"
    _description = "WooCommerce Instance Operations"

    @api.model
    def _get_default_ks_woo_instances_ids(self):
        """
        :return: ks.woo.connector.instance() All the active WooCommerce Instances
        """
        instance_ids = self.env['ks.woo.connector.instance'].search([('ks_instance_state', '=', 'active')]).ids
        return [(6, 0, instance_ids)]

    ks_instances = fields.Many2many('ks.woo.connector.instance', string="Instance", required=True,
                                    default=lambda self: self._get_default_ks_woo_instances_ids(),
                                    help="Displays WooCommerce Instance Name")
    ks_check_multi_operation = fields.Boolean(string="Perform Multiple Operation", required=True)
    ks_operation_flow = fields.Selection([('woo_to_odoo', 'WooCommerce to Odoo'),
                                          ('odoo_to_woo', 'Odoo to WooCommerce')], default="woo_to_odoo",
                                         string="Operation Flow",
                                         help="Shows the flow of the operation either from WooCommerce to Odoo or Odoo to WooCommerce")
    ks_operation_odoo = fields.Selection([('import_product', 'Import Product'),
                                          ('import_stock', 'Import Stock'),
                                          ('import_attributes', 'Import Product Attributes'),
                                          ('import_categories', 'Import Categories'),
                                          ('import_tags', 'Import Tags'),
                                          ('import_coupons', 'Import Coupons'),
                                          ('import_orders', 'Import Orders'),
                                          ('import_orders_status', 'Import Orders Status'),
                                          ('import_customers', 'Import Customers'),
                                          ('import_shipping_methods', 'Import Shipping Methods'),
                                          ('import_payment_gateway', "Import Payment Gateway"),
                                          ], string="Import Operation",
                                         help="It include the list of operation that can be performed for Import Operation")
    ks_operation_woo = fields.Selection([('export_product', 'Export Product'),
                                         ('export_attributes', 'Export Attributes'),
                                         ('export_categories', 'Export Categories'),
                                         ('export_tags', 'Export Tags'),
                                         ('export_coupons', 'Export Coupons'),
                                         ('export_customers', 'Export Customers'),
                                         ('export_orders', 'Export Orders'),
                                         ('export_stocks', 'Export Stocks')
                                         ], string="Export Operation",
                                        help="It include the list of operation that can be performed for Export Operation")
    ks_want_all = fields.Boolean(string="Want to select all operations ?",
                                 help=" Checkbox allows you to select all the operation at one click`")
    ks_want_all_woo = fields.Boolean(string="Want to select all operations ? ")
    ks_sync_products = fields.Boolean(string="Sync Products")
    ks_sync_taxes = fields.Boolean(string="Sync Taxes")
    ks_sync_attribute = fields.Boolean(string="Sync Attributes")
    ks_sync_tags = fields.Boolean(string="Sync Tags")
    ks_sync_category = fields.Boolean(string="Sync Category")
    ks_stock = fields.Boolean(string="Sync Stocks")
    ks_sync_customers = fields.Boolean(string="Sync Customers")
    ks_sync_orders = fields.Boolean(string="Import Orders")
    ks_sync_coupons = fields.Boolean(string="Sync Coupons")
    ks_sync_payment_gateways = fields.Boolean(string="Sync Payment Gateways")
    ks_publish_products = fields.Boolean(string="Publish Product")
    ks_unpublish_products = fields.Boolean(string="Unpublish Product")
    ks_update_customers = fields.Boolean(string="Export/Update Customers")
    ks_update_products = fields.Boolean(string="Export/Update Products")
    ks_update_products_with_images = fields.Boolean(string="Export/Update Products with Images")
    ks_update_coupons = fields.Boolean(string="Export/Update Coupons")
    ks_update_attributes = fields.Boolean(string="Export/Update Attributes")
    ks_update_category = fields.Boolean(string="Export/Update Categories")
    ks_update_tags = fields.Boolean(string="Export/Update Tags")
    ks_update_order_status = fields.Boolean(string="Update Order status")
    ks_update_order = fields.Boolean(string="Export New Orders")
    ks_update_stock = fields.Boolean(string="Update Stock")
    ks_record_ids = fields.Char(string="Record ID", help="Enter woo id for that particular records")
    ks_date_filter_before = fields.Datetime(string="Date Before", help="Displays the date before")
    ks_date_filter_after = fields.Datetime(string="Date After", help="Displays the date after")
    ks_value_example = fields.Char(default="For multiple record separate Woo Id(s) using ','. For example: 111,222,333",
                                   readonly=True)
    ks_get_specific_import_type = fields.Selection([('import_all', "Import All "),
                                                    ('record_id', 'Specific Id Filter'),
                                                    ('date_filter', 'Date Filter')],
                                                   string="Import with",
                                                   help="It include the list of types of import functionalities.")
    ks_product_stock_selects = fields.Many2many("ks.woo.product.template", string="Product Ids")
    ks_get_specific_export_type = fields.Selection(
        [('export_all', 'Export All'), ('record_id', 'Specific Id Filter'), ('date_filter', 'Date Filter')],default='export_all',
        string='Export with', help="It include the list of types of export functionalities.")
    ks_exports_all = fields.Boolean(string='All Export')
    ks_update_details = fields.Boolean(string='Basic Information', default=True)
    ks_update_price = fields.Boolean(string='Set Price in Woo')
    ks_update_image = fields.Boolean(string='Set Image in Woo')
    ks_update_stocks = fields.Boolean(string='Set Stock in Woo')
    ks_update_website_status = fields.Selection([('published', 'Published'), ('unpublished', 'Unpublished')],
                                                string='Website Status', default='published')
    ks_export_image_variation = fields.Boolean(string='Export Variation Images',
                                               help="Enables/disables - Variable profile image to be exported with product")

    @api.onchange('ks_get_specific_export_type')
    def on_change_state(self):
        if self.ks_get_specific_export_type:
            if self.ks_get_specific_export_type == "export_all":
                self.ks_exports_all = True
            else:
                self.ks_exports_all = False
        else:
            self.ks_exports_all = False

    def check_for_valid_record_id(self):
        if not self.ks_record_ids:
            return self.env['ks.message.wizard'].ks_pop_up_message(names='Info',
                                                                   message="Please provide Woo Id of record for import.")
        if self.ks_record_ids:
            if '-' in self.ks_record_ids:
                woo_record_ids = self.ks_record_ids.split('-')
                for i in woo_record_ids:
                    try:
                        int(i)
                    except Exception:
                        return self.env['ks.message.wizard'].ks_pop_up_message(names='Info',
                                                                               message="Please enter valid Woo Id of record for import.")
            else:
                woo_record_ids = self.ks_record_ids.split(',')
                for i in woo_record_ids:
                    try:
                        int(i)
                    except Exception:
                        return self.env['ks.message.wizard'].ks_pop_up_message(names='Info',
                                                                           message="Please enter valid Woo Id of record for import.")
        return False

    @api.onchange('ks_get_specific_import_type', 'ks_operation_odoo')
    def ks_check_api(self):
        if self.ks_get_specific_import_type == 'date_filter' and self.ks_operation_odoo in ['import_attributes',
                                                                                            'import_customers',
                                                                                            'import_categories',
                                                                                            'import_tags',
                                                                                            'import_payment_gateway',
                                                                                            'import_tax',
                                                                                            'import_shipping_methods'
                                                                                            ]:
            raise ValidationError("Selected Import Operation does not support Date Filter")
        if self.ks_get_specific_import_type == 'record_id' and self.ks_operation_odoo in ['import_attributes',
                                                                                          'import_payment_gateway',
                                                                                          'import_tax','import_shipping_methods']:
            raise ValidationError("Selected Import Operation does not support Specific Filter")
        if self.ks_get_specific_import_type == 'import_all' and self.ks_operation_odoo in ['import_orders_status']:
            raise ValidationError("Selected Import Operation does not support Import All Filter")
    @api.onchange('ks_get_specific_export_type', 'ks_operation_woo')
    def ks_check_export_api(self):
        if self.ks_get_specific_export_type == 'date_filter' and self.ks_operation_woo in ['export_attributes', 'export_categories', 'export_tags', 'export_coupons', 'export_customers', 'export_orders', 'export_stocks']:
            raise ValidationError("Selected Export Operation does not support Date Filter")
        if self.ks_get_specific_export_type == 'record_id' and self.ks_operation_woo in ['export_attributes', 'export_categories', 'export_tags', 'export_coupons', 'export_customers', 'export_orders', 'export_stocks']:
            raise ValidationError("Selected Export Operation does not support Specific Filter")

    @api.onchange('ks_want_all')
    def ks_check_all(self):
        if self.ks_want_all:
            self.ks_stock = self.ks_sync_products = self.ks_sync_tags = self.ks_sync_category = self.ks_sync_attribute \
                = self.ks_sync_coupons = self.ks_sync_orders = \
                self.ks_sync_payment_gateways = self.ks_sync_customers = True
        elif not self.ks_want_all:
            self.ks_stock = self.ks_sync_products = self.ks_sync_tags = self.ks_sync_category = self.ks_sync_attribute \
                = self.ks_sync_coupons = self.ks_sync_orders = \
                self.ks_sync_payment_gateways = self.ks_sync_customers = False

    @api.onchange('ks_want_all_woo')
    def ks_check_all_woo(self):
        if self.ks_want_all_woo:
            self.ks_update_attributes = self.ks_update_tags = self.ks_update_stock = self.ks_update_coupons = \
                self.ks_update_customers = self.ks_update_products = self.ks_update_products_with_images = \
                self.ks_update_category = self.ks_publish_products = self.ks_unpublish_products = \
                self.ks_update_order_status = True
        elif not self.ks_want_all_woo:
            self.ks_update_attributes = self.ks_update_tags = self.ks_update_stock = self.ks_update_coupons = \
                self.ks_update_customers = self.ks_update_products = self.ks_update_products_with_images = \
                self.ks_update_category = self.ks_publish_products = self.ks_unpublish_products = \
                self.ks_update_order_status = False

    def ks_execute_operation(self):
        if self.ks_operation_flow == 'odoo_to_woo' and (
                not self.ks_operation_woo and not self.ks_update_stock and not self.ks_update_coupons \
                and not self.ks_update_order and not self.ks_update_customers and not self.ks_update_category and \
                not self.ks_update_tags and not self.ks_update_attributes \
                and not self.ks_update_products and not self.ks_sync_payment_gateways \
                and not self.ks_sync_coupons and not self.ks_sync_orders and not self.ks_sync_customers and not \
                        self.ks_stock and not self.ks_sync_category and not self.ks_sync_tags and not self.ks_sync_attribute and \
                not self.ks_sync_products):
            raise ValidationError("Please select operation")
        if self.ks_operation_flow == 'woo_to_odoo' and (not self.ks_operation_odoo and not self.ks_sync_payment_gateways \
                                                        and not self.ks_sync_coupons and not self.ks_sync_orders and not self.ks_sync_customers and not \
                                                                self.ks_stock and not self.ks_sync_category and not self.ks_sync_tags and not self.ks_sync_attribute and \
                                                        not self.ks_sync_products and not self.ks_update_coupons \
                                                        and not self.ks_update_order and not self.ks_update_customers and not self.ks_update_stock and not self.ks_update_category and \
                                                        not self.ks_update_tags and not self.ks_update_attributes and not self.ks_update_products and not self.ks_sync_taxes):
            raise ValidationError("Please select operation")
        if not self.ks_operation_flow:
            raise ValidationError("Please select operation flow")
        if self.ks_get_specific_import_type == 'date_filter' and self.ks_operation_odoo in ['import_attributes',
                                                                                            'import_customers',
                                                                                            'import_categories',
                                                                                            'import_orders_status',
                                                                                            'import_tags',
                                                                                            'import_payment_gateway',
                                                                                            'import_shipping_methods']:
            raise ValidationError("Cannot Execute! Selected Import Operation does not support Date Filter")
        if self.ks_get_specific_import_type == 'record_id' and self.ks_operation_odoo in ['import_attributes',
                                                                                          'import_shipping_methods']:
            raise ValidationError("Cannot Execute! Selected Import Operation does not support Specific Record Filter")

        for instance in self.ks_instances:
            if instance.ks_instance_state == 'active':
                try:
                    if not self.ks_check_multi_operation and self.ks_operation_flow == 'woo_to_odoo' and \
                            self.ks_get_specific_import_type == 'record_id':
                        if_not_valid = self.check_for_valid_record_id()
                        if if_not_valid:
                            return if_not_valid
                        if self.ks_operation_odoo == 'import_tax':
                            _logger.info('Tax Entry on Queue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            record_list = ""
                            if '-' in self.ks_record_ids:
                                woo_record_ids = self.ks_record_ids.split('-')
                                start_id = int(woo_record_ids[0])
                                end_id = int(woo_record_ids[1]) + 1
                                for id in range(start_id, end_id):
                                    record_list = record_list + str(id) + ","
                                record_list = record_list[:-1]
                            else:
                                record_list = self.ks_record_ids
                            taxes_json_records = self.env['account.tax'].ks_woo_get_all_account_tax(
                                instance=instance,
                                include=record_list)
                            if taxes_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_taxes_record_in_queue(instance=instance,
                                                                                              data=taxes_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='tax',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message="Tax Sync operation to queue jobs failed",
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_operation_odoo == 'import_customers':
                            _logger.info('Customer Entry on Queue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            record_list = ""
                            if '-' in self.ks_record_ids:
                                woo_record_ids = self.ks_record_ids.split('-')
                                start_id = int(woo_record_ids[0])
                                end_id = int(woo_record_ids[1]) + 1
                                for id in range(start_id, end_id):
                                    record_list = record_list + str(id) + ","
                                record_list = record_list[:-1]
                            else:
                                record_list = self.ks_record_ids
                            customer_json_records = self.env['ks.woo.partner'].ks_woo_get_all_customers(
                                instance=instance,
                                include=record_list)
                            if customer_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance=instance,
                                                                                                 data=customer_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='customer',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message="Customer Sync operation to queue jobs failed",
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")

                        elif self.ks_operation_odoo == 'import_categories':
                            _logger.info("Categories Entry on Queue start for WooCommerce Instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            record_list = ""
                            if '-' in self.ks_record_ids:
                                woo_record_ids = self.ks_record_ids.split('-')
                                start_id = int(woo_record_ids[0])
                                end_id = int(woo_record_ids[1]) + 1
                                for id in range(start_id, end_id):
                                    record_list = record_list + str(id) + ","
                                record_list = record_list[:-1]
                            else:
                                record_list = self.ks_record_ids
                            category_json_records = self.env['ks.woo.product.category'].ks_woo_get_all_product_category(
                                instance=instance, include=record_list)
                            if category_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(instance=instance,
                                                                                                 data=category_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='category',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Category Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")

                        elif self.ks_operation_odoo == 'import_product':
                            _logger.info('Product enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            record_list = ""
                            if '-' in self.ks_record_ids:
                                woo_record_ids = self.ks_record_ids.split('-')
                                start_id = int(woo_record_ids[0])
                                end_id = int(woo_record_ids[1])+1
                                for id in range(start_id,end_id):
                                    record_list = record_list + str(id) + ","
                                record_list = record_list[:-1]
                            else:
                                record_list = self.ks_record_ids
                            product_json_records = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                                instance=instance, include=record_list)
                            if product_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=instance,
                                                                                                data=product_json_records)

                        elif self.ks_operation_odoo == 'import_stock':
                            _logger.info("Stock importing start for woocommerce instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            record_list = ""
                            if '-' in self.ks_record_ids:
                                woo_record_ids = self.ks_record_ids.split('-')
                                start_id = int(woo_record_ids[0])
                                end_id = int(woo_record_ids[1]) + 1
                                for id in range(start_id, end_id):
                                    record_list = record_list + str(id) + ","
                                record_list = record_list[:-1]
                            else:
                                record_list = self.ks_record_ids
                            product_json_records = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                                instance=instance, include=record_list)
                            if product_json_records:
                                self.env['ks.woo.queue.jobs'].ks_import_stock_woocommerce_in_queue(instance=instance,
                                                                                                   data=product_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='import',
                                                                              ks_type='stock',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Stock sync failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        elif self.ks_operation_odoo == 'import_tags':
                            _logger.info("Product Tags enqueue start for woocommerce instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            record_list = ""
                            if '-' in self.ks_record_ids:
                                woo_record_ids = self.ks_record_ids.split('-')
                                start_id = int(woo_record_ids[0])
                                end_id = int(woo_record_ids[1]) + 1
                                for id in range(start_id, end_id):
                                    record_list = record_list + str(id) + ","
                                record_list = record_list[:-1]
                            else:
                                record_list = self.ks_record_ids
                            tags_json_records = self.env['ks.woo.product.tag'].ks_woo_get_all_product_tag(
                                instance=instance, include=record_list)
                            if tags_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(instance=instance,
                                                                                            data=tags_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='tags',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Tags Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        elif self.ks_operation_odoo == 'import_coupons':
                            _logger.info('Coupons enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            record_list = ""
                            if '-' in self.ks_record_ids:
                                woo_record_ids = self.ks_record_ids.split('-')
                                start_id = int(woo_record_ids[0])
                                end_id = int(woo_record_ids[1]) + 1
                                for id in range(start_id, end_id):
                                    record_list = record_list + str(id) + ","
                                record_list = record_list[:-1]
                            else:
                                record_list = self.ks_record_ids
                            coupons_json_records = self.env['ks.woo.coupons'].ks_woo_get_all_coupon(
                                instance=instance, include=record_list)
                            if coupons_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=instance,
                                                                                               data=coupons_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='coupon',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Coupons Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        elif self.ks_operation_odoo == 'import_orders':
                            _logger.info('Orders enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            record_list = ""
                            if '-' in self.ks_record_ids:
                                woo_record_ids = self.ks_record_ids.split('-')
                                start_id = int(woo_record_ids[0])
                                end_id = int(woo_record_ids[1]) + 1
                                for id in range(start_id, end_id):
                                    record_list = record_list + str(id) + ","
                                record_list = record_list[:-1]
                            else:
                                record_list = self.ks_record_ids
                            # filter the order status selected on instance to be synced
                            order_status = ','.join(instance.ks_order_status.mapped('status'))
                            orders_json_records = self.env['sale.order'].ks_get_all_woo_orders(
                                instance=instance, status=order_status, include=record_list)
                            if orders_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=instance,
                                                                                              data=orders_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='order',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Orders Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        elif self.ks_operation_odoo == 'import_orders_status':
                            _logger.info('Orders enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            # filter the order status selected on instance to be synced
                            # order_status = ','.join(instance.ks_order_status.mapped('status'))
                            orders_json_records = self.env['sale.order'].ks_get_all_woo_orders(
                                instance=instance, include=self.ks_record_ids)
                            if orders_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=instance,
                                                                                              data=orders_json_records,update=True)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='order',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Orders Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                    if not self.ks_check_multi_operation and self.ks_operation_flow == 'woo_to_odoo' and \
                            self.ks_get_specific_import_type == 'date_filter':
                        '''Note all the other domains does not supports date 
                        filter and we have handled it above in line 81-88'''
                        if self.ks_operation_odoo == 'import_product':
                            _logger.info('Product enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            product_json_records = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                                instance=instance, date_after=self.ks_date_filter_after,
                                date_before=self.ks_date_filter_before)
                            if product_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=instance,
                                                                                                data=product_json_records)
                        elif self.ks_operation_odoo == 'import_coupons':
                            _logger.info('Coupons enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            coupons_json_records = self.env['ks.woo.coupons'].ks_woo_get_all_coupon(
                                instance=instance, date_after=self.ks_date_filter_after,
                                date_before=self.ks_date_filter_before)
                            if coupons_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=instance,
                                                                                               data=coupons_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='coupon',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Coupons Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        elif self.ks_operation_odoo == 'import_orders':
                            _logger.info('Orders enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            # filter the order status selected on instance to be synced
                            order_status = ','.join(instance.ks_order_status.mapped('status'))
                            orders_json_records = self.env['sale.order'].ks_get_all_woo_orders(
                                instance=instance, status=order_status, date_after=self.ks_date_filter_after,
                                date_before=self.ks_date_filter_before)
                            if orders_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=instance,
                                                                                              data=orders_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='order',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Orders Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        elif self.ks_operation_odoo == 'import_stock':
                            _logger.info("Stock importing start for woocommerce instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            product_json_records = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                                instance=instance, date_after=self.ks_date_filter_after,
                                date_before=self.ks_date_filter_before)
                            if product_json_records:
                                self.env['ks.woo.queue.jobs'].ks_import_stock_woocommerce_in_queue(instance=instance,
                                                                                                   data=product_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='import',
                                                                              ks_type='stock',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Stock sync failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                    if not self.ks_check_multi_operation and self.ks_operation_flow == 'woo_to_odoo' and \
                            self.ks_get_specific_import_type == 'import_all':
                        if self.ks_operation_odoo == 'import_shipping_methods':
                            _logger.info('Shipping Methods enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            shipping_method_json_records = self.env[
                                'ks.woo.delivery.carrier'].ks_woo_get_all_shipping_methods(instance_id=instance)
                            if shipping_method_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_shipping_record_in_queue(instance=instance,
                                                                                                  data=shipping_method_json_records)
                        if self.ks_operation_odoo == "import_attributes":
                            _logger.info('Attribute enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            attribute_json_records = self.env['ks.woo.product.attribute'].ks_woo_get_all_attributes(
                                instance_id=instance)
                            if attribute_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(instance=instance,
                                                                                                  data=attribute_json_records)
                        if self.ks_operation_odoo == 'import_tax':
                            _logger.info('Tax Entry on Queue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            taxes_json_records = self.env['account.tax'].ks_woo_get_all_account_tax(
                                instance=instance,
                                include=self.ks_record_ids)
                            if taxes_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_taxes_record_in_queue(instance=instance,
                                                                                              data=taxes_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='tax',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message="Tax Sync operation to queue jobs failed",
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_operation_odoo == "import_tags":
                            _logger.info('Tags enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            tags_json_records = self.env['ks.woo.product.tag'].ks_woo_get_all_product_tag(
                                instance=instance)
                            if tags_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(instance=instance,
                                                                                            data=tags_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='tags',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Tags Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_operation_odoo == "import_categories":
                            _logger.info("Categories Entry on Queue start for WooCommerce Instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            category_json_records = self.env['ks.woo.product.category'].ks_woo_get_all_product_category(
                                instance=instance)
                            if category_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(instance=instance,
                                                                                                 data=category_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='category',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Category Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_operation_odoo == "import_payment_gateway":
                            # Sync Payment Gateways
                            _logger.info("Payment Gateways enqueue starts for Woocommerce Instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            pg_json_records = self.env['ks.woo.payment.gateway'].ks_woo_get_all_payment_gateway(
                                instance=instance)
                            if pg_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_pg_record_in_queue(instance=instance,
                                                                                           data=pg_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='payment_gateway',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Payment Gateway Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_operation_odoo == "import_customers":
                            # Sync Customers
                            _logger.info('Customer enqueue For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            customer_json_records = self.env['ks.woo.partner'].ks_woo_get_all_customers(
                                instance=instance)
                            if customer_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance=instance,
                                                                                                 data=customer_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='customer',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message="Customer Sync operation to queue jobs failed",
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_operation_odoo == 'import_product':
                            _logger.info('Product enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            product_json_records = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                                instance=instance)
                            if product_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=instance,
                                                                                                data=product_json_records)
                        if self.ks_operation_odoo == 'import_stock':
                            _logger.info("Stock importing start for woocommerce instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            product_json_records = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                                instance=instance)
                            if product_json_records:
                                self.env['ks.woo.queue.jobs'].ks_import_stock_woocommerce_in_queue(instance=instance,
                                                                                                   data=product_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='import',
                                                                              ks_type='stock',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Stock sync failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_operation_odoo == "import_coupons":
                            _logger.info('Coupons enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            coupons_json_records = self.env['ks.woo.coupons'].ks_woo_get_all_coupon(
                                instance=instance)
                            if coupons_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=instance,
                                                                                               data=coupons_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='coupon',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Coupons Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        elif self.ks_operation_odoo == 'import_orders':
                            _logger.info('Orders enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            # filter the order status selected on instance to be synced
                            order_status = ','.join(instance.ks_order_status.mapped('status'))
                            orders_json_records = self.env['sale.order'].ks_get_all_woo_orders(
                                instance=instance, status=order_status)
                            if orders_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=instance,
                                                                                              data=orders_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='order',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Orders Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                    product_config = {
                        "image": self.ks_update_image,
                        "price": self.ks_update_price,
                        "variant_image": self.ks_export_image_variation,
                        "stock": self.ks_update_stocks,
                        "basic_info": self.ks_update_details,
                        "web_status": self.ks_update_website_status,
                        "server_action": True
                    }
                    if not self.ks_check_multi_operation and self.ks_operation_flow == 'odoo_to_woo' and self.ks_get_specific_export_type == 'record_id':
                        if_not_valid = self.check_for_valid_record_id()
                        if if_not_valid:
                            return if_not_valid
                        if self.ks_operation_woo == 'export_product':
                            _logger.info('Product entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            self.env['product.template'].ks_get_odoo_products(instance=instance, include=self.ks_record_ids, product_config=product_config)
                        else:
                            self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                          ks_type='product',
                                                                          ks_woo_instance=instance,
                                                                          ks_record_id=0,
                                                                          ks_message="Product Sync operation to queue jobs failed",
                                                                          ks_woo_id=0,
                                                                          ks_operation_flow='woo_to_odoo',
                                                                          ks_status="failed")
                    if not self.ks_check_multi_operation and self.ks_operation_flow == 'odoo_to_woo' and self.ks_get_specific_export_type == 'date_filter':
                        if self.ks_operation_woo == 'export_product':
                            _logger.info('Product entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            self.env['product.template'].get_product_id(instance=instance, date_after=self.ks_date_filter_after,
                                date_before=self.ks_date_filter_before, product_config=product_config)
                        else:
                            self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                          ks_type='product',
                                                                          ks_woo_instance=instance,
                                                                          ks_record_id=0,
                                                                          ks_message="Product Sync operation to queue jobs failed",
                                                                          ks_woo_id=0,
                                                                          ks_operation_flow='woo_to_odoo',
                                                                          ks_status="failed")

                    if not self.ks_check_multi_operation and self.ks_operation_flow == 'odoo_to_woo':
                        if self.ks_operation_woo == 'export_attributes' and self.ks_exports_all:
                            _logger.info('Attribute entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            attribute_records = self.env['ks.woo.product.attribute'].search(
                                [('ks_wc_instance.id', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(instance,
                                                                                              records=attribute_records)
                        elif self.ks_operation_woo == 'export_categories' and self.ks_exports_all:
                            _logger.info("Category Records Enqueue for Woocommerce Instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            category_records = self.env['ks.woo.product.category'].search([
                                ('ks_wc_instance.id', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(instance,
                                                                                             records=category_records)
                        elif self.ks_operation_woo == 'export_tags' and self.ks_exports_all:
                            _logger.info('Tags entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            tag_records = self.env['ks.woo.product.tag'].search([
                                ('ks_wc_instance', '=', instance.id)
                            ])
                            self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(instance,
                                                                                        records=tag_records)
                        elif self.ks_operation_woo == 'export_product' and self.ks_exports_all:
                            _logger.info('Product entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            product_records = self.env['ks.woo.product.template'].search([
                                ('ks_wc_instance', '=', instance.id)
                            ])
                            self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance,
                                                                                            records=product_records)
                        elif self.ks_operation_woo == 'export_stocks' and self.ks_exports_all:
                            _logger.info('Stocks enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            for rec in self.ks_product_stock_selects:
                                _logger.info('Stocks enqueued for product [%s -(%s)]'
                                             , rec.ks_woo_product_id, rec.ks_name)
                                self.env['ks.woo.queue.jobs'].ks_create_product_stock_record_in_queue(instance,
                                                                                                      records=rec)
                        elif self.ks_operation_woo == 'export_customers' and self.ks_exports_all:
                            _logger.info('Customer enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            customer_records = self.env['ks.woo.partner'].search(
                                [('ks_wc_instance.id', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance,
                                                                                             records=customer_records)
                        elif self.ks_operation_woo == 'export_coupons' and self.ks_exports_all:
                            _logger.info('Coupons enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            coupon_records = self.env['ks.woo.coupons'].search(
                                [('ks_wc_instance.id', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=instance,
                                                                                           records=coupon_records)
                        elif self.ks_operation_woo == 'export_orders' and self.ks_exports_all:
                            _logger.info('Orders enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            order_records = self.env['sale.order'].search(
                                [('ks_wc_instance', '=', instance.id),
                                 ('ks_woo_order_id', '=', 0)])
                            self.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=instance,
                                                                                          records=order_records)
                        # elif self.ks_operation_woo == 'export_coupons' and self.ks_exports_all:
                        #     _logger.info('Coupons enqueue start For WooCommerce Instance [%s -(%s)]'
                        #                  , instance.ks_instance_name, instance.id)
                        #     coupon_records = self.env['ks.woo.coupons'].search(
                        #         [('ks_wc_instance.id', '=', instance.id)])
                        #     self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=instance,
                        #                                                                    records=coupon_records)

                    if self.ks_check_multi_operation:
                        if self.ks_update_attributes:
                            _logger.info('Attribute entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            attribute_records = self.env['ks.woo.product.attribute'].search(
                                [('ks_wc_instance.id', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(instance,
                                                                                              records=attribute_records)
                        if self.ks_update_order:
                            _logger.info('Order entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            order_records = self.env['sale.order'].search(
                                [('ks_wc_instance', '=', instance.id),
                                 ('ks_woo_order_id', '=', 0)])
                            self.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=instance,
                                                                                          records=order_records)
                        if self.ks_sync_taxes:
                            _logger.info('Tax Entry on Queue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            taxes_json_records = self.env['account.tax'].ks_woo_get_all_account_tax(
                                instance=instance,
                                include=self.ks_record_ids)
                            if taxes_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_taxes_record_in_queue(instance=instance,
                                                                                              data=taxes_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='Tax',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message="Tax Sync operation to queue jobs failed",
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_update_category:
                            _logger.info('Category entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            category_records = self.env['ks.woo.product.category'].search([
                                ('ks_wc_instance.id', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(instance,
                                                                                             records=category_records)
                        if self.ks_update_stock:
                            _logger.info('Stocks enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            product_stock_records = self.env['ks.woo.product.template'].search(
                                [('ks_wc_instance', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_product_stock_record_in_queue(instance,
                                                                                                  records=product_stock_records)
                        if self.ks_update_tags:
                            _logger.info('Tags entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            tag_records = self.env['ks.woo.product.tag'].search([
                                ('ks_wc_instance', '=', instance.id)
                            ])
                            self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(instance,
                                                                                        records=tag_records)
                        if self.ks_update_products:
                            _logger.info('Product entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            product_records = self.env['ks.woo.product.template'].search([
                                ('ks_wc_instance', '=', instance.id)
                            ])
                            self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance,
                                                                                            records=product_records)
                        if self.ks_update_coupons:
                            _logger.info('Coupons enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            coupon_records = self.env['ks.woo.coupons'].search(
                                [('ks_wc_instance.id', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=instance,
                                                                                           records=coupon_records)
                        if self.ks_update_customers:
                            # Update Customers on woo
                            _logger.info('Customer entry enqueue for WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            customer_records = self.env['ks.woo.partner'].search(
                                [('ks_wc_instance.id', '=', instance.id)])
                            self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance,
                                                                                             records=customer_records)
                        if self.ks_sync_orders:
                            _logger.info('Orders enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            # filter the order status selected on instance to be synced
                            order_status = ','.join(instance.ks_order_status.mapped('status'))
                            orders_json_records = self.env['sale.order'].ks_get_all_woo_orders(
                                instance=instance, status=order_status)
                            if orders_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_order_record_in_queue(instance=instance,
                                                                                              data=orders_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='order',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Orders Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_sync_customers:
                            # Sync Customers
                            _logger.info('Customer enqueue For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            customer_json_records = self.env['ks.woo.partner'].ks_woo_get_all_customers(
                                instance=instance)
                            if customer_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance=instance,
                                                                                                 data=customer_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='customer',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message="Customer Sync operation to queue jobs failed",
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_sync_coupons:
                            _logger.info('Coupons enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            coupons_json_records = self.env['ks.woo.coupons'].ks_woo_get_all_coupon(
                                instance=instance)
                            if coupons_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(instance=instance,
                                                                                               data=coupons_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='coupon',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Coupons Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_stock:
                            _logger.info("Stock importing start for woocommerce instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            product_json_records = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                                instance=instance)
                            if product_json_records:
                                self.env['ks.woo.queue.jobs'].ks_import_stock_woocommerce_in_queue(
                                    instance=instance,
                                    data=product_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='import',
                                                                              ks_type='stock',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Stock sync failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_sync_products:
                            _logger.info('Product enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            product_json_records = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                                instance=instance)
                            if product_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=instance,
                                                                                                data=product_json_records)
                        if self.ks_sync_attribute:
                            _logger.info('Attribute enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            attribute_json_records = self.env[
                                'ks.woo.product.attribute'].ks_woo_get_all_attributes(
                                instance_id=instance)
                            if attribute_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(
                                    instance=instance,
                                    data=attribute_json_records)
                        if self.ks_sync_category:
                            _logger.info("Categories Entry on Queue start for WooCommerce Instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            category_json_records = self.env['ks.woo.product.category'].ks_woo_get_all_product_category(
                                instance=instance)
                            if category_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(instance=instance,
                                                                                                 data=category_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='category',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Category Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_sync_tags:
                            _logger.info('Tags enqueue start For WooCommerce Instance [%s -(%s)]'
                                         , instance.ks_instance_name, instance.id)
                            tags_json_records = self.env['ks.woo.product.tag'].ks_woo_get_all_product_tag(
                                instance=instance)
                            if tags_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(instance=instance,
                                                                                            data=tags_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='tags',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Tags Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                        if self.ks_sync_payment_gateways:
                            # Sync Payment Gateways
                            _logger.info("Payment Gateways enqueue starts for Woocommerce Instance [%s -(%s)]",
                                         instance.ks_instance_name, instance.id)
                            pg_json_records = self.env['ks.woo.payment.gateway'].ks_woo_get_all_payment_gateway(
                                instance=instance)
                            if pg_json_records:
                                self.env['ks.woo.queue.jobs'].ks_create_pg_record_in_queue(instance=instance,
                                                                                           data=pg_json_records)
                            else:
                                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                              ks_type='payment_gateway',
                                                                              ks_woo_instance=instance,
                                                                              ks_record_id=0,
                                                                              ks_message='Payment Gateway Sync operation to queue jobs failed',
                                                                              ks_woo_id=0,
                                                                              ks_operation_flow='woo_to_odoo',
                                                                              ks_status="failed")
                except ConnectionError:
                    self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                  ks_type='system_status',
                                                                  ks_woo_instance=instance,
                                                                  ks_record_id=0,
                                                                  ks_message="Sync operation to queue jobs failed due to ",
                                                                  ks_woo_id=0,
                                                                  ks_status="failed",
                                                                  ks_operation_flow='woo_to_odoo',
                                                                  ks_error=ConnectionError)
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                                  ks_type='system_status',
                                                                  ks_woo_instance=instance,
                                                                  ks_record_id=0,
                                                                  ks_message="Sync operation to queue jobs failed due to",
                                                                  ks_woo_id=0,
                                                                  ks_operation_flow='woo_to_odoo',
                                                                  ks_status="failed",
                                                                  ks_error=e)
        cron_record = self.env.ref('ks_woocommerce.ks_ir_cron_job_process')
        if cron_record:
            next_exc_time = datetime.now()
            cron_record.sudo().write({'nextcall': next_exc_time, 'active': True})
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Info', message="WooCommerce Operations has "
                                                                                     "been performed, Please refer "
                                                                                     "logs for further details.")
