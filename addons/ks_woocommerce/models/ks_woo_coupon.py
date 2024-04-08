# -*- coding: utf-8 -*-

import logging
import datetime

from odoo import models, fields, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class KsWooCommerceCoupons(models.Model):
    _name = "ks.woo.coupons"
    _description = 'WooCommerce Coupons'
    _rec_name = 'ks_coupon_code'

    ks_coupon_code = fields.Char('Coupon Code', required=True, help="Displays Woocommerce Coupon Code")
    ks_wc_instance = fields.Many2one('ks.woo.connector.instance', string='Instance', required=True, help="Displays WooCommerce Instance Name")
    ks_amount = fields.Float('Amount', help="Displays amount of discount")
    ks_discount_type = fields.Selection([('fixed_cart', 'Fixed Cart Discount'), ('percent', 'Percentage Discount'),
                                         ('fixed_product', 'Fixed Product Discount')], default="fixed_cart",
                                        string="Discount Type", help="Displays Type of discount")
    ks_description = fields.Text(string="Description")
    ks_individual_use = fields.Boolean(string='Individual Use', help="Enables/Disable Individual Use of Coupons")
    ks_exclude_sale_items = fields.Boolean(string='Exclude Sale Items', help="Enables/Disable Exclude Sale Items")
    ks_usage_limit_per_user = fields.Integer(string="Usage limit per user", help="Displays Usage limit per user for coupon")
    ks_limit_usage_to_x_items = fields.Integer(string="Limit usage to X items")
    ks_usage_limit = fields.Integer(string="Usage limit per coupon", help="Displays Usage limit per coupon")
    ks_allowed_email = fields.Char(string="Allowed emails", help="Displays Allowed Emails with comma")
    ks_free_shipping = fields.Boolean(string="Allow Free Shipping", help="Enables/Disables the Free shipping")
    ks_expiry_date = fields.Date(string="Expiry Date", help="Displays Expiry Date of Coupon")
    ks_minimum_amount = fields.Float(string='Minimum Spend', help="Displays Minimum Spend Amount")
    ks_maximum_amount = fields.Float(string='Maximum Spend', help="Displays Maximum Spend Amount")
    ks_incl_product = fields.Text(string="Included Product Templates ids", readonly=True)
    ks_excl_product = fields.Text(string="Excluded Product Variants ids", readonly=True)
    ks_incl_cat = fields.Text(string="Included Categories", readonly=True)
    ks_excl_cat = fields.Text(string="Excluded Categories", readonly=True)
    ks_woo_coupon_id = fields.Integer('Woo Coupon ID', readonly=True,
                                      help=_("the record id of the particular record defied in the Connector"))
    ks_date_created = fields.Datetime('Date Created', help=_("The date on which the record is created on the Connected"
                                                             " Connector Instance"), readonly=True)
    ks_date_updated = fields.Datetime('Date Updated', help=_("The latest date on which the record is updated on the"
                                                             " Connected Connector Instance"), readonly=True)
    ks_include_product_template = fields.Many2many("ks.woo.product.template", 'ks_woo_product_template_include_rel',
                                                   string="Products", domain="[('ks_woo_product_id', '!=', 0), "
                                                                             "('ks_wc_instance', '=', ks_wc_instance)]", help="Displays list of Included Product for Coupon")
    ks_exclude_product_template = fields.Many2many("ks.woo.product.template", 'ks_woo_product_template_exclude_rel',
                                                   string="Exclude Products",
                                                   domain="[('ks_woo_product_id', '!=', 0), "
                                                          "('ks_wc_instance', '=', ks_wc_instance)]", help="Displays list of Excluded Product for Coupon")
    ks_include_product_variant = fields.Many2many("ks.woo.product.variant", 'ks_woo_product_variant_include_rel',
                                                  string="Include Product Variant",
                                                  domain="[('ks_woo_variant_id', '!=', 0), "
                                                         "('ks_wc_instance', '=', ks_wc_instance)]", help="Displays list of Include Product Variant for Coupon")
    ks_exclude_product_variant = fields.Many2many("ks.woo.product.variant", 'ks_woo_product_variant_exclude_rel',
                                                  string="Exclude Product Variant",
                                                  domain="[('ks_woo_variant_id', '!=', 0), "
                                                         "('ks_wc_instance', '=', ks_wc_instance)]", help="Displays list of Exclude Product Variant for Coupon")
    ks_include_categories = fields.Many2many("ks.woo.product.category", 'ks_woo_coupon_include_product_category_rel',
                                             'product_category_id', 'ks_include_categories_id',
                                             string="Product Categories",
                                             domain="[('ks_woo_category_id', '!=', 0), "
                                                    "('ks_wc_instance', '=', ks_wc_instance)]", help="Displays list of Included Product Categories for Coupon")
    ks_exclude_categories = fields.Many2many("ks.woo.product.category", 'ks_woo_coupon_exclude_product_category_rel',
                                             'product_category_id', 'ks_exclude_categories_id',
                                             string="Exclude Product Categories",
                                             domain="[('ks_woo_category_id', '!=', 0), "
                                                    "('ks_wc_instance', '=', ks_wc_instance)]", help="Displays list of Excluded Product Categories for Coupon")

    ks_data = fields.Text('Json Data', help=_("Holds the data we got from API"), readonly=True)
    ks_need_update = fields.Boolean('Update', help=_("This will need to determine if a record needs to be updated, Once user "
                                           "update the record it will set as False"), readonly=True)
    ks_company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,
                                    required=True, readonly=True, help=" Shows the name of the company")

    ks_sync_date = fields.Datetime('Modified On', readonly=True,
                                   help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On',readonly=True)
    ks_sync_status = fields.Boolean('Sync Status', compute='sync_update', default=False)

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
            if rec.ks_woo_coupon_id:
                values.update({'ks_sync_date': datetime.datetime.now()})

        return super(KsWooCommerceCoupons, self).write(values)

    def ks_create_coupon_odoo_to_woo(self, queue_record=False):
        """
        create coupon from odoo model to woo
        :param queue_record: record reference for queue
        :return: json data response from api
        """
        woo_instance = False
        try:
            woo_instance = self.ks_wc_instance
            json_data = self.ks_prepare_export_json_data()
            if woo_instance and not self.ks_woo_coupon_id:
                coupon_data = self.ks_woo_post_coupon(json_data, woo_instance)
                if coupon_data:
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(coupon_data, self,
                                                                                     'ks_woo_coupon_id')
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_woo",
                                                                       ks_model='ks.woo.coupons',
                                                                       ks_layer_model='ks.woo.coupons',
                                                                       ks_message="Coupons export create success",
                                                                       ks_status="success",
                                                                       ks_type="coupon",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="odoo_to_woo",
                                                                       ks_woo_id=coupon_data.get(
                                                                           "id", 0),
                                                                       ks_woo_instance=woo_instance)
                    self.ks_sync_date = datetime.datetime.now()
                    self.ks_last_exported_date = self.ks_sync_date
                    self.sync_update()
                    return coupon_data
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                   ks_model='ks.woo.coupons',
                                                                   ks_layer_model='ks.woo.coupons',
                                                                   ks_message=str(e),
                                                                   ks_status="failed",
                                                                   ks_type="coupon",
                                                                   ks_record_id=self.id,
                                                                   ks_operation_flow="odoo_to_woo",
                                                                   ks_woo_id=0,
                                                                   ks_woo_instance=woo_instance)

    def ks_update_coupon_odoo_to_woo(self, queue_record=False):
        """
        Updates the odoo model record on woo
        param queue_record: record reference for queue
        """
        woo_instance = False
        try:
            woo_instance = self.ks_wc_instance
            json_data = self.ks_prepare_export_json_data()
            if woo_instance and self.ks_woo_coupon_id:
                coupon_data = self.ks_woo_update_coupon(self.ks_woo_coupon_id, json_data, woo_instance)
                if coupon_data:
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(coupon_data, self,
                                                                                     'ks_woo_coupon_id')
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_woo",
                                                                       ks_model='ks.woo.coupons',
                                                                       ks_layer_model='ks.woo.coupons',
                                                                       ks_message="Coupons export update success",
                                                                       ks_status="success",
                                                                       ks_type="coupon",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="odoo_to_woo",
                                                                       ks_woo_id=coupon_data.get(
                                                                           "id", 0),
                                                                       ks_woo_instance=woo_instance)
                    self.ks_sync_date = datetime.datetime.now()
                    self.ks_last_exported_date = self.ks_sync_date
                    self.sync_update()

        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                               ks_model='ks.woo.coupons',
                                                               ks_layer_model='ks.woo.coupons',
                                                               ks_message=str(e),
                                                               ks_status="failed",
                                                               ks_type="coupon",
                                                               ks_record_id=self.id,
                                                               ks_operation_flow="odoo_to_woo",
                                                               ks_woo_id=0,
                                                               ks_woo_instance=woo_instance)

    def ks_action_sync_coupons_from_woo(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_woo_coupon_id and e.ks_wc_instance)
                if len(records) > 0:
                    for dat in records:
                        data = [self.ks_woo_get_coupon(dat.ks_woo_coupon_id, dat.ks_wc_instance)]
                        if data[0]:
                            self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(data=data,
                                                                                           instance=dat.ks_wc_instance)
                return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                       '''Product Coupons Records enqueued in Queue 
                                                                       Please refer Queue and logs for further details
                                                                       ''')
            except Exception as e:
                raise e

        else:
            try:
                self.ensure_one()
                if self.ks_woo_coupon_id and self.ks_wc_instance:
                    data = self.ks_woo_get_coupon(self.ks_woo_coupon_id, self.ks_wc_instance)
                    if data:
                        self.ks_woo_import_coupon_update(data)
                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Action Performed. Please refer logs for further details.
                                                                           ''')
            except Exception as e:
                raise e

    def ks_action_sync_coupons_to_woo(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance)
                if len(records):
                    self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(records=records)

                return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                       'Product Coupons Records enqueued in Queue Please refer Queue and logs for further details')

            except Exception as e:
                raise e

        else:
            try:
                self.ensure_one()
                if self.ks_woo_coupon_id and self.ks_wc_instance:
                    self.ks_update_coupon_odoo_to_woo()
                elif not self.ks_woo_coupon_id and self.ks_wc_instance:
                    coupon = self.ks_create_coupon_odoo_to_woo()

                return self.env["ks.message.wizard"].ks_pop_up_message("success", "Action Performed. Please refer logs for further details.")

            except Exception as e:
                raise e

    def ks_prepare_export_json_data(self):
        data = {
            "code": self.ks_coupon_code,
            "amount": str(self.ks_amount),
            "discount_type": self.ks_discount_type,
            "description": self.ks_description or '',
            "date_expires": self.ks_expiry_date.strftime("%Y-%m-%dT%H:%M:%S") if self.ks_expiry_date else '',
            "individual_use": self.ks_individual_use,
            "product_ids": self.ks_find_woo_include_product_ids(),
            "excluded_product_ids": self.ks_find_woo_exclude_product_ids(),
            "usage_limit": self.ks_usage_limit,
            "usage_limit_per_user": self.ks_usage_limit_per_user,
            "limit_usage_to_x_items": self.ks_limit_usage_to_x_items,
            "free_shipping": self.ks_free_shipping,
            "product_categories": self.ks_include_categories.mapped('ks_woo_category_id'),
            "excluded_product_categories": self.ks_exclude_categories.mapped('ks_woo_category_id'),
            "exclude_sale_items": self.ks_exclude_sale_items,
            "minimum_amount": str(self.ks_minimum_amount),
            "maximum_amount": str(self.ks_maximum_amount),
            "email_restrictions": list(self.ks_allowed_email.split(",")) if self.ks_allowed_email else ''
        }
        return data

    def ks_odoo_update_coupon_action(self):
        """
        action server method to import attributes from woo
        :return:
        """
        coupons_with_woo_id = self.filtered(lambda e: e.ks_woo_coupon_id and e.ks_wc_instance)
        if len(coupons_with_woo_id) > 1:
            try:
                for rec in coupons_with_woo_id:
                    coupon_data_response = self.ks_woo_get_coupon(rec.ks_woo_coupon_id, rec.ks_wc_instance)
                    if coupon_data_response:
                        self.env['ks.woo.queue.jobs'].ks_create_coupon_record_in_queue(rec.ks_wc_instance,
                                                                                       data=[
                                                                                           coupon_data_response])
                    else:
                        self.env['ks.woo.logger'].ks_create_log_param(ks_woo_instance=rec.ks_wc_instance,
                                                                      ks_operation_performed='fetch',
                                                                      ks_type='coupon',
                                                                      ks_record_id=rec.id,
                                                                      ks_woo_id=rec.ks_woo_coupon_id,
                                                                      ks_operation_flow='woo_to_odoo',
                                                                      ks_status='failed',
                                                                      ks_message="Coupon Enqueue to queue jobs failed")

            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param(ks_woo_instance=self.ks_wc_instance,
                                                              ks_operation_performed='fetch',
                                                              ks_type='coupon',
                                                              ks_record_id=0,
                                                              ks_woo_id=0,
                                                              ks_operation_flow='woo_to_odoo',
                                                              ks_status='failed',
                                                              ks_message="Coupon Enqueue to queue jobs failed",
                                                              ks_error=e)
            else:
                return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                       '''Attributes Records enqueued in Queue 
                                                                       Please refer Queue and logs for further details
                                                                       ''')
        else:
            self.ensure_one()
            coupon_data_response = self.ks_woo_get_coupon(coupons_with_woo_id.ks_woo_coupon_id,
                                                          coupons_with_woo_id.ks_wc_instance)
            self.ks_woo_import_coupon_update(coupon_data_response)
        return self.env['ks.message.wizard'].ks_pop_up_message("Done",
                                                               '''Operation performed, Please refer Logs and Queues for 
                                                               further Details.''')

    def ks_woo_import_coupon_update(self, coupon_data, queue_record=False):
        try:
            coupon_json = self.ks_prepare_import_json_data(coupon_data, self.ks_wc_instance)
            if coupon_json:
                self.write(coupon_json)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(coupon_data, self,
                                                                                 'ks_woo_coupon_id')
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                   ks_model='ks.woo.coupons',
                                                                   ks_layer_model='ks.woo.coupons',
                                                                   ks_message="Product coupons import update success",
                                                                   ks_status="success",
                                                                   ks_type="coupon",
                                                                   ks_record_id=self.id,
                                                                   ks_operation_flow="woo_to_odoo",
                                                                   ks_woo_id=coupon_data.get(
                                                                       "id", 0),
                                                                   ks_woo_instance=self.ks_wc_instance)
                self.ks_sync_date = datetime.datetime.now()
                self.ks_last_exported_date = self.ks_sync_date
                self.sync_update()
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                               ks_model='ks.woo.coupons',
                                                               ks_layer_model='ks.woo.coupons',
                                                               ks_message=str(e),
                                                               ks_status="failed",
                                                               ks_type="coupon",
                                                               ks_record_id=self.id,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=coupon_data.get(
                                                                   "id", 0),
                                                               ks_woo_instance=self.ks_wc_instance)

    def ks_woo_import_coupon_create(self, coupon_data, instance, queue_record=False):
        try:
            coupon_json = self.ks_prepare_import_json_data(coupon_data, instance)
            if coupon_json:
                coupon_record = self.create(coupon_json)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(coupon_data, coupon_record,
                                                                                 'ks_woo_coupon_id')
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                   ks_model='ks.woo.coupons',
                                                                   ks_layer_model='ks.woo.coupons',
                                                                   ks_message="Product coupons import create success",
                                                                   ks_status="success",
                                                                   ks_type="coupon",
                                                                   ks_record_id=coupon_record.id,
                                                                   ks_operation_flow="woo_to_odoo",
                                                                   ks_woo_id=coupon_data.get(
                                                                       "id", 0),
                                                                   ks_woo_instance=instance)
                coupon_record.ks_sync_date = datetime.datetime.now()
                coupon_record.ks_last_exported_date = coupon_record.ks_sync_date
                coupon_record.sync_update()
                return coupon_record
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                               ks_model='ks.woo.coupons',
                                                               ks_layer_model='ks.woo.coupons',
                                                               ks_message=str(e),
                                                               ks_status="failed",
                                                               ks_type="coupon",
                                                               ks_record_id=0,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=coupon_data.get(
                                                                   "id", 0),
                                                               ks_woo_instance=instance)

    def ks_manage_coupon_woo_data(self, instance_id, json_data):
        coupon_exist_in_odoo = self.search([('ks_woo_coupon_id', '=', json_data.get('id')),
                                            ('ks_wc_instance', '=', instance_id.id)], limit=1)
        if coupon_exist_in_odoo:
            coupon_exist_in_odoo.ks_woo_import_coupon_update(json_data)
            ks_operation_type = 'update'
        else:
            coupon_exist_in_odoo = coupon_exist_in_odoo.ks_woo_import_coupon_create(json_data, instance_id)
            ks_operation_type = 'create'

        _logger.info("Coupon Management Operation completed with coupon record id %s and the operation type %s",
                     coupon_exist_in_odoo.id, ks_operation_type)

    def ks_manage_product_templates_include(self, instance, coupon_data):
        """
        :param instance: ks.woo.connector.instance()
        :param coupon_data: woo json data
        :return: all product data
        """
        included_product_templ = []
        included_product_var = []
        product_ids = coupon_data.get("product_ids", "")
        if product_ids:
            for id in product_ids:
                product_templ_found = self.env['ks.woo.product.template'].search([('ks_woo_product_id', '=', id),
                                                                                  ('ks_wc_instance', '=', instance.id)])
                product_var_found = self.env['ks.woo.product.variant'].search([('ks_woo_variant_id', '=', id),
                                                                               ('ks_wc_instance', '=', instance.id)])
                if product_templ_found:
                    included_product_templ.append(product_templ_found.id)
                elif product_var_found:
                    included_product_var.append(product_var_found.id)
        return included_product_templ, included_product_var

    def ks_manage_product_templates_exclude(self, instance, coupon_data):
        """
        :param instance: ks.woo.connector.instance()
        :param coupon_data: coupon_json_data
        :return: ids which are present on the layer
        """
        excluded_product_templ = []
        excluded_product_var = []
        excluded_product_ids = coupon_data.get("excluded_product_ids")
        if excluded_product_ids:
            for id in excluded_product_ids:
                product_templ_found = self.env['ks.woo.product.template'].search([('ks_woo_product_id', '=', id),
                                                                                  ('ks_wc_instance', '=', instance.id)])
                product_var_found = self.env['ks.woo.product.variant'].search([('ks_woo_variant_id', '=', id),
                                                                               ('ks_wc_instance', '=', instance.id)])
                if product_templ_found:
                    excluded_product_templ.append(product_templ_found.id)
                elif product_var_found:
                    excluded_product_var.append(product_var_found.id)

        return excluded_product_templ, excluded_product_var

    def ks_manage_category_include(self, instance, coupon_data):
        """
        :param instance: ks.woo.connector.instance()
        :param coupon_data: coupon json data
        :return: ids of category layer records
        """
        incl_cats = []
        category_ids = coupon_data.get("product_categories")
        if category_ids:
            for id in category_ids:
                cat_found = self.env['ks.woo.product.category'].search([("ks_wc_instance", '=', instance.id),
                                                                        ("ks_woo_category_id", '=', id)])
                if cat_found:
                    incl_cats.append(cat_found.id)
        return incl_cats

    def ks_manage_category_exclude(self, instance, coupon_data):
        """
        :param instance: ks.woo.connector.instance()
        :param coupon_data: coupon json data
        :return: category layer records ids
        """
        excl_cats = []
        excl_category_ids = coupon_data.get("excluded_product_categories")
        if excl_category_ids:
            for id in excl_category_ids:
                cat_found = self.env['ks.woo.product.category'].search([("ks_wc_instance", '=', instance.id),
                                                                        ("ks_woo_category_id", '=', id)])
                if cat_found:
                    excl_cats.append(cat_found.id)

        return excl_cats

    def ks_prepare_import_json_data(self, coupon_data, instance):
        data = {
            "ks_coupon_code": coupon_data.get('code').upper() or '',
            "ks_amount": float(coupon_data.get('amount') or 0),
            "ks_discount_type": coupon_data.get('discount_type') or '',
            "ks_description": coupon_data.get('description') or '',
            "ks_expiry_date": coupon_data.get('date_expires') or coupon_data.get('expiry_date') or False,
            "ks_individual_use": coupon_data.get('individual_use'),
            "ks_usage_limit": coupon_data.get('usage_limit') or '',
            "ks_usage_limit_per_user": coupon_data.get('usage_limit_per_user') or '',
            "ks_limit_usage_to_x_items": coupon_data.get('limit_usage_to_x_items') or '',
            "ks_free_shipping": coupon_data.get('free_shipping'),
            "ks_exclude_sale_items": coupon_data.get('exclude_sale_items') or '',
            "ks_minimum_amount": float(coupon_data.get('minimum_amount') or 0),
            "ks_maximum_amount": float(coupon_data.get('maximum_amount') or 0),
            "ks_allowed_email": ",".join(coupon_data.get('email_restrictions')),
            "ks_wc_instance": instance.id,
            "ks_incl_product": str(coupon_data.get("product_ids", [])),
            "ks_excl_product": str(coupon_data.get("excluded_product_ids", [])),
            "ks_incl_cat": str(coupon_data.get("product_categories", [])),
            "ks_excl_cat": str(coupon_data.get("excluded_product_categories", []))
        }
        if coupon_data.get("product_ids"):
            incl_templ, incl_var = self.ks_manage_product_templates_include(instance, coupon_data)
            data.update({
                "ks_include_product_template": [(6, 0, incl_templ)],
                "ks_include_product_variant": [(6, 0, incl_var)]
            })
        if coupon_data.get("excluded_product_ids"):
            excl_templ, excl_var = self.ks_manage_product_templates_exclude(instance, coupon_data)
            data.update({
                "ks_exclude_product_template": [(6, 0, excl_templ)],
                "ks_exclude_product_variant": [(6, 0, excl_var)]
            })
        if coupon_data.get("product_categories"):
            incl_cats = self.ks_manage_category_include(instance, coupon_data)
            data.update({
                'ks_include_categories': [(6, 0, incl_cats)]
            })
        if coupon_data.get("excluded_product_categories"):
            excl_cats = self.ks_manage_category_exclude(instance, coupon_data)
            data.update({
                "ks_exclude_categories": [(6, 0, excl_cats)]
            })
        return data

    def ks_woo_get_all_coupon(self, instance, include=False, date_before=False, date_after=False):
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = None
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
            params = {'per_page': per_page, 'page': page}
        try:
            while multi_api_call:
                wc_api = instance.ks_woo_api_authentication()
                coupon_data_response = wc_api.get("coupons", params=params)
                if coupon_data_response.status_code in [200, 201]:
                    all_retrieved_data = coupon_data_response.json()
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="coupon",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.coupons",
                                                                       message=str(coupon_data_response.text))
                total_api_calls = coupon_data_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                    params.update({'page': page})
                else:
                    multi_api_call = False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="coupon",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.coupons",
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="coupon",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance,
                                                               woo_id=0,
                                                               layer_model="ks.woo.coupons",
                                                               message="Fetch of Coupons successful")
            return all_retrieved_data

    def ks_woo_get_coupon(self, coupon_id, instance):
        """
        Get specific product coupon from WooCommerce
        :param coupon_id: Woocommerce Coupon ID
        :param instance: WooCommerce instance
        :return: json response
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            coupon_data_response = wc_api.get("coupons/%s" % coupon_id)
            coupon_data = False
            if coupon_data_response.status_code in [200, 201]:
                coupon_data = coupon_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="coupon",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=coupon_data.get("id"),
                                                                   layer_model="ks.woo.coupons",
                                                                   message="Fetch of Coupons successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="coupon",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.coupons",
                                                                   message=str(coupon_data_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="coupon",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.coupons",
                                                               message=str(e))
        else:
            return coupon_data

    def ks_woo_post_coupon(self, data, instance):
        """
        Function to create the coupon
        :param data: data to create the tag
        :param instance: woocommerce instance
        :return: json response
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            coupon_data_response = wc_api.post("coupons", data)
            coupon_data = False
            if coupon_data_response.status_code in [200, 201]:
                coupon_data = coupon_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="coupon",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=coupon_data.get("id"),
                                                                   layer_model="ks.woo.coupons",
                                                                   message="Create of Coupons successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="coupon",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.coupons",
                                                                   message=str(coupon_data_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="coupon",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.coupons",
                                                               message=str(e))
        else:
            return coupon_data

    def ks_woo_update_coupon(self, coupon_id, data, instance):
        """
        Function to update the product coupons
        :param data: data to update the coupon
        :param instance: woocommerce instance
        :return: json response
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            coupon_response = wc_api.put("coupons/%s" % coupon_id, data)
            coupon_data = False
            if coupon_response.status_code in [200, 201]:
                coupon_data = coupon_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_post",
                                                                   status="success",
                                                                   type="coupon",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=coupon_data.get("id"),
                                                                   layer_model="ks.woo.coupons",
                                                                   message="Update of Coupons successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="coupon",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.coupons",
                                                                   message=str(coupon_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="coupon",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.coupons",
                                                               message=str(e))
        else:
            return coupon_data

    def ks_find_woo_include_product_ids(self):
        product = []
        if self.ks_include_product_variant:
            product.extend(self.ks_include_product_variant.mapped("ks_woo_variant_id"))
        if self.ks_include_product_template:
            product.extend(self.ks_include_product_template.mapped("ks_woo_product_id"))
        return product

    def ks_find_woo_exclude_product_ids(self):
        product = []
        if self.ks_exclude_product_variant:
            product.extend(self.ks_exclude_product_variant.mapped("ks_woo_variant_id"))
        if self.ks_exclude_product_template:
            product.extend(self.ks_exclude_product_template.mapped("ks_woo_product_id"))
        return product
