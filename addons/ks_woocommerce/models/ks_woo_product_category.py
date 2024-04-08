# -*- coding: utf-8 -*-
import logging
import datetime

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class KsModelProductCategory(models.Model):
    _name = 'ks.woo.product.category'
    _rec_name = "ks_product_category"
    _description = "Woo Product Category"

    ks_slug = fields.Char(string="Slug", help="Displays WooCommerce Category Slug")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", readonly=True,
                                     help=_("WooCommerce Connector Instance reference"),
                                     ondelete='cascade')

    ks_woo_category_id = fields.Integer('Woo Category ID', readonly=True,
                                        help=_("the record id of the particular record defied in the Connector"))
    ks_date_created = fields.Datetime('Date Created', help=_("The date on which the record is created on the Connected"
                                                             " Connector Instance"), readonly=True)
    ks_date_updated = fields.Datetime('Date Updated', help=_("The latest date on which the record is updated on the"
                                                             " Connected Connector Instance"), readonly=True)
    ks_product_category = fields.Many2one('product.category', ondelete='cascade', string="Odoo Product Category ",
                                          readonly=True, help="Displays Odoo Product Category Reference")
    ks_description = fields.Text('Description')
    ks_mapped = fields.Boolean(string="Manual Mapping", readonly = True)

    ks_sync_date = fields.Datetime('Modified On',readonly=True, help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On', readonly=True)
    ks_sync_status = fields.Boolean('Sync Status', compute='sync_update', default=False)

    def sync_update(self):
        for rec in self:
            if rec.ks_last_exported_date and rec.ks_sync_date:
                ks_reduced_ks_sync_time = rec.ks_last_exported_date - datetime.timedelta(seconds=10)
                ks_increased_ks_sync_time = rec.ks_last_exported_date + datetime.timedelta(seconds=10)
                if ks_reduced_ks_sync_time < rec.ks_sync_date < ks_increased_ks_sync_time:
                    rec.ks_sync_status = True
                else:
                    rec.ks_sync_status = False
            else:
                rec.ks_sync_status = False

    def write(self, values):
        for rec in self:
            if rec.ks_woo_category_id:
                values.update({'ks_sync_date': datetime.datetime.now()})

        return super(KsModelProductCategory, self).write(values)

    def check_if_already_prepared(self, instance, product_category):
        """
        Checks if record is already prepared to be imported on layer model
        :param instance: woocommerce instance
        :param product_category: ks_woo_product_catrgory()
        :return: product_category
        """
        product_category_exists = self.search([('ks_wc_instance', '=', instance.id),
                                               ('ks_product_category', '=', product_category.id)], limit=1)
        if product_category_exists:
            return product_category_exists
        else:
            return False

    def ks_woo_post_category(self, data, instance, product_template):
        """
        Create category on woo api
        :param data: data to create
        :param instance: woo instance
        :return: json response
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            category_data_response = wc_api.post("products/categories", data)
            if category_data_response.status_code in [200, 201]:
                category_data = category_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="category",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=product_template,
                                                                   woo_id=category_data.get("id"),
                                                                   layer_model="ks.woo.product.category",
                                                                   message="Create of Category successful")
                return category_data

            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="category",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=product_template,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.category",
                                                                   message=str(category_data_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="category",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               ks_record_id=product_template,
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.category",
                                                               message=str(e))

    def ks_woo_update_category(self, category_id, data, instance):
        """
        updates category on woo
        :param category_id: id of the woo category
        :param data: catgeory json data
        :param instance: woo instance
        :return: json response data
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            woo_category_response = wc_api.put("products/categories/%s" % category_id, data)
            if woo_category_response.status_code in [200, 201]:
                category_data = woo_category_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_post",
                                                                   status="success",
                                                                   type="category",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=category_data.get("id"),
                                                                   layer_model="ks.woo.product.category",
                                                                   message="Update of Category successful")
                return category_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="category",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.category",
                                                                   message=str(woo_category_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="category",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.category",
                                                               message=str(e))

    def ks_woo_get_all_product_category(self, instance, include=False):
        """
        Use: This function will get all the category from WooCommerce
           :woo_instance: woo instance
           :include : parameter to filter out records
           :return: Dictionary of Created Woo category
           :rtype: dict
                       """
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = []
        if include:
            params = {'per_page': per_page,
                      'page': page,
                      'include': include}
        else:
            params = {'per_page': per_page,
                      'page': page}
        try:
            while multi_api_call:
                wc_api = instance.ks_woo_api_authentication()
                category_data_response = wc_api.get("products/categories", params=params)
                if category_data_response.status_code in [200, 201]:
                    all_retrieved_data.extend(category_data_response.json())
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="category",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.product.category",
                                                                       message=str(category_data_response.text))
                total_api_calls = category_data_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                    params.update({'page': page})
                else:
                    multi_api_call = False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="category",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.category",
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="category",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance,
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.category",
                                                               message="Fetch of Category successful")
            return all_retrieved_data

    def ks_woo_get_category(self, category_id, instance):
        """
        get specific category from woocommrece api
        :param category_id: Id of category
        :param instance: woo instance
        :return: json response
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            category_data_response = wc_api.get("products/categories/%s" % category_id)
            category_data = False
            if category_data_response.status_code in [200, 201]:
                category_data = category_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="category",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=category_data.get("id"),
                                                                   layer_model="ks.woo.product.category",
                                                                   message="Fetch of Category successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="category",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.category",
                                                                   message=str(category_data_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="category",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.category",
                                                               message=str(e))
        else:
            return category_data

    def ks_woo_import_product_category(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance and e.ks_woo_category_id)
                if len(records):
                    for dat in records:
                        json_data = [self.ks_woo_get_category(dat.ks_woo_category_id, dat.ks_wc_instance)]
                        if json_data[0]:
                            self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(data=json_data,
                                                                                             instance=dat.ks_wc_instance)

                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Category Records enqueued in Queue 
                                                                           Please refer Queue and logs for further details
                                                                           ''')

            except Exception as e:
                raise e

        else:
            try:
                self.ensure_one()
                json_data = self.ks_woo_get_category(self.ks_woo_category_id, self.ks_wc_instance)
                if json_data:
                    self.ks_manage_catgeory_import(self.ks_wc_instance, json_data)
                return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                       "Action Performed. Please refer logs for further details.")

            except Exception as e:
                raise e

    def ks_woo_export_product_category(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance)
                if len(records):
                    self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(records=records)

                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Product Coupons Records enqueued in Queue 
                                                                           Please refer Queue and logs for further details
                                                                           ''')

            except Exception as e:
                raise e

        else:
            try:
                self.ensure_one()
                self.ks_manage_category_export()
                return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                       "Action Performed. Please refer logs for further details.")

            except Exception as e:
                raise e

    def ks_manage_catgeory_import(self, instance, category_json, queue_record=False):
        """
        :param instance: ks.woo.connector.instance()
        :param category_json: catgeory json response from woo
        :param queue_record: boolean trigger for queue
        :return:
        """
        all_category = [category_json]
        parent_category = None
        odoo_category = None
        try:
            if category_json:
                while category_json.get("parent"):
                    woo_category_json = self.ks_woo_get_category(category_json.get("parent"), instance)
                    all_category.append(woo_category_json)
                    category_json = woo_category_json
            if all_category:
                all_category.reverse()
                for index, data in enumerate(all_category):
                    layer_category = self.search([('ks_wc_instance', '=', instance.id),
                                                  ("ks_woo_category_id", '=', data.get("id"))])
                    odoo_category = layer_category.ks_product_category
                    if layer_category:
                        try:
                            odoo_main_data = self.ks_map_product_category_data_for_odoo(data, instance, odoo_category)
                            odoo_category.ks_update_data_in_odoo(odoo_category,
                                                                 odoo_main_data)
                            layer_data = self.ks_map_product_category_data_for_layer(data, odoo_category, instance)
                            layer_category.write(layer_data)
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_status="success",
                                                                               ks_type="category",
                                                                               ks_woo_instance=instance,
                                                                               ks_woo_id=data.get("id", 0),
                                                                               ks_record_id=layer_category.id,
                                                                               ks_message="Category import update success.",
                                                                               ks_model="product.category",
                                                                               ks_layer_model="ks.woo.product.category"
                                                                               )
                            layer_category.ks_sync_date = datetime.datetime.now()
                            layer_category.ks_last_exported_date = layer_category.ks_sync_date
                            layer_category.sync_update()
                        except Exception as e:
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_status="failed",
                                                                               ks_type="category",
                                                                               ks_woo_instance=instance,
                                                                               ks_woo_id=data.get("id", 0),
                                                                               ks_record_id=layer_category.id,
                                                                               ks_message=str(e),
                                                                               ks_model="product.category",
                                                                               ks_layer_model="ks.woo.product.category"
                                                                               )

                    else:
                        try:
                            odoo_main_data = self.ks_map_product_category_data_for_odoo(data, instance)
                            odoo_category = self.env['product.category'].ks_create_data_in_odoo(odoo_main_data)
                            layer_data = self.ks_map_product_category_data_for_layer(data, odoo_category, instance)
                            layer_category = self.create(layer_data)
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_status="success",
                                                                               ks_type="category",
                                                                               ks_woo_instance=instance,
                                                                               ks_woo_id=data.get("id", 0),
                                                                               ks_record_id=layer_category.id,
                                                                               ks_message="Category import create success.",
                                                                               ks_model="product.category",
                                                                               ks_layer_model="ks.woo.product.category"
                                                                               )
                            layer_category.ks_sync_date = datetime.datetime.now()
                            layer_category.ks_last_exported_date = layer_category.ks_sync_date
                            layer_category.sync_update()
                        except Exception as e:
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_status="failed",
                                                                               ks_type="category",
                                                                               ks_woo_instance=instance,
                                                                               ks_woo_id=data.get("id", 0),
                                                                               ks_record_id=0,
                                                                               ks_message=str(e),
                                                                               ks_model="product.category",
                                                                               ks_layer_model="ks.woo.product.category"
                                                                               )
                    if not index:
                        parent_category = odoo_category
                        continue
                    if parent_category:
                        odoo_category.parent_id = parent_category.id
                    parent_category = odoo_category
            return odoo_category
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            raise e

    def ks_manage_category_export(self, queue_record=False, product_template=False):
        """
        :param queue_record: Queue Boolean Trigger
        :return: json response
        """
        woo_category_data_response = None
        odoo_base_category = self.ks_product_category
        if odoo_base_category:
            hierarchy = self.ks_product_category.parent_path.split('/')[:-1]
            parent = 0
            try:
                for id in hierarchy:
                    product_category = odoo_base_category.search([('id', '=', int(id))])
                    if product_category.ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).ks_woo_category_id:
                        try:
                            category_id = product_category.ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).ks_woo_category_id
                            woo_category_data = self.ks_prepare_export_json_data(product_category,
                                                                                 product_category.ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id))
                            woo_category_data.update({"parent": parent})
                            woo_category_data_response = self.ks_woo_update_category(category_id, woo_category_data,
                                                                                     self.ks_wc_instance)
                            if woo_category_data_response:
                                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(
                                    woo_category_data_response,
                                    product_category.ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id),
                                    'ks_woo_category_id',
                                    {
                                        "ks_slug": woo_category_data_response.get(
                                            'slug') or ''}
                                )
                                self.ks_product_category.browse(int(id)).ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).ks_sync_date = datetime.datetime.now()
                                self.ks_product_category.browse(int(id)).ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).ks_last_exported_date = self.ks_product_category.browse(int(id)).ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).ks_sync_date
                                self.ks_product_category.browse(int(id)).ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).sync_update()
                                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_woo",
                                                                                   ks_operation_flow="odoo_to_woo",
                                                                                   ks_status="success",
                                                                                   ks_type="category",
                                                                                   ks_woo_instance=self.ks_wc_instance,
                                                                                   ks_woo_id=woo_category_data_response.get(
                                                                                       "id", 0),
                                                                                   ks_record_id=self.id,
                                                                                   ks_message="Category Export update successfull",
                                                                                   ks_model="product.category",
                                                                                   ks_layer_model="ks.woo.product.category"
                                                                                   )
                        except Exception as e:
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                               ks_operation_flow="odoo_to_woo",
                                                                               ks_status="failed",
                                                                               ks_type="category",
                                                                               ks_woo_instance=self.ks_wc_instance,
                                                                               ks_woo_id=0,
                                                                               ks_record_id=self.id,
                                                                               ks_message=str(e),
                                                                               ks_model="product.category",
                                                                               ks_layer_model="ks.woo.product.category"
                                                                               )
                    else:
                        try:
                            woo_category_data = self.ks_prepare_export_json_data(product_category,
                                                                                 product_category.ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id))
                            woo_category_data.update({"parent": parent})
                            woo_category_data_response = self.ks_woo_post_category(woo_category_data,
                                                                                   self.ks_wc_instance, product_template)
                            if woo_category_data_response:
                                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(
                                    woo_category_data_response,
                                    product_category.ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id),
                                    'ks_woo_category_id',
                                    {
                                        "ks_slug": woo_category_data_response.get(
                                            'slug') or ''}
                                )
                                self.ks_product_category.browse(int(id)).ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).ks_sync_date = datetime.datetime.now()
                                self.ks_product_category.browse(int(id)).ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).ks_last_exported_date = self.ks_product_category.browse(int(id)).ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).ks_sync_date
                                self.ks_product_category.browse(int(id)).ks_product_category.filtered(lambda x:x.ks_wc_instance.id == self.ks_wc_instance.id).sync_update()
                                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_woo",
                                                                                   ks_operation_flow="odoo_to_woo",
                                                                                   ks_status="success",
                                                                                   ks_type="category",
                                                                                   ks_woo_instance=self.ks_wc_instance,
                                                                                   ks_woo_id=woo_category_data_response.get(
                                                                                       "id", 0),
                                                                                   ks_record_id=self.id,
                                                                                   ks_message="Category Export create successful",
                                                                                   ks_model="product.category",
                                                                                   ks_layer_model="ks.woo.product.category"
                                                                                   )
                        except Exception as e:
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                               ks_operation_flow="odoo_to_woo",
                                                                               ks_status="failed",
                                                                               ks_type="category",
                                                                               ks_woo_instance=self.ks_wc_instance,
                                                                               ks_woo_id=0,
                                                                               ks_record_id=self.id,
                                                                               ks_message=str(e),
                                                                               ks_model="product.category",
                                                                               ks_layer_model="ks.woo.product.category"
                                                                               )

                    if woo_category_data_response:
                        parent = woo_category_data_response.get("id")

                return woo_category_data_response
            except Exception as e:
                if queue_record:
                    queue_record.ks_update_failed_state()
            # Add Loggers here

    def ks_get_parent_ids(self, odoo_category):
        """
        :param odoo_category:product.category()
        :return: parents ids
        """
        return odoo_category.parent_path.split('/')[:-1]

    def create_woo_record(self, instance, odoo_category, export_to_woo=False, queue_record=False):
        """
        :param instance: ks.woo.connector.instance()
        :param odoo_category: odoo main record
        :param export_to_woo: boolean, want to directly export or not
        :param queue_record: boolean trigger for queue job
        :return:
        """
        try:
            layer_category = None
            parent_ids = self.ks_get_parent_ids(odoo_category)
            for id in parent_ids:
                category_exists = self.search([('ks_product_category', '=', int(id)),
                                               ('ks_wc_instance', '=', instance.id)])
                if not category_exists:
                    product_category = self.env['product.category'].search([('id', '=', int(id))])
                    data = self.ks_map_prepare_data_for_layer(instance, product_category)
                    layer_category = self.create(data)

                    if export_to_woo:
                        try:
                            layer_category.ks_manage_category_export()
                        except Exception as e:
                            _logger.info(str(e))
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                   status="success",
                                                                   type="category",
                                                                   instance=instance,
                                                                   odoo_model="product.category",
                                                                   layer_model="ks.woo.product.category",
                                                                   id=layer_category.id,
                                                                   message="Layer preparation Success")

            return layer_category
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                   status="failed",
                                                                   type="category",
                                                                   instance=instance,
                                                                   odoo_model="product.category",
                                                                   layer_model="ks.woo.product.category",
                                                                   id=odoo_category.id,
                                                                   message=str(e))

    def update_woo_record(self, instance, odoo_category, export_to_woo=False, queue_record=False):
        """
        :param instance: ks.woo.connector.instance()
        :param odoo_category: product.category()
        :param export_to_woo: boolean, if want to export the record directly on woocommerce
        :param queue_record: boolean trigger for queue job
        :return:
        """
        try:
            parent_ids = self.ks_get_parent_ids(odoo_category)
            for id in parent_ids:
                category_exists = self.search([('ks_product_category', '=', int(id)),
                                               ('ks_wc_instance', '=', instance.id)])
                if category_exists:
                    product_category = self.env['product.category'].search([('id', '=', int(id))])
                    data = self.ks_map_prepare_data_for_layer(instance, product_category)
                    category_exists.write(data)
                    if export_to_woo:
                        try:
                            category_exists.ks_manage_category_export()
                        except Exception as e:
                            _logger.info(str(e))
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                   status="success",
                                                                   type="category",
                                                                   instance=instance,
                                                                   odoo_model="product.category",
                                                                   layer_model="ks.woo.product.category",
                                                                   id=category_exists.id,
                                                                   message="Layer Preparation Successful")
            return category_exists

        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()

            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                   status="failed",
                                                                   type="category",
                                                                   instance=instance,
                                                                   odoo_model="product.category",
                                                                   layer_model="ks.woo.product.category",
                                                                   id=odoo_category.id,
                                                                   message=str(e))

    def ks_prepare_export_json_data(self, odoo_category, layer_category):
        """
        prepares to export data to woo
        :return: data
        """
        data = {
            "name": odoo_category.name if odoo_category.name else '',
            "slug": layer_category.ks_slug if layer_category.ks_slug else '',
            "description": layer_category.ks_description if layer_category.ks_description else ''
        }
        return data

    def ks_map_product_category_data_for_odoo(self, json_data, instance=False, odoo_category=False):
        """
        Map json data for odoo model create
        :param json_data: data fro api
        :return: data
        """
        data = None
        if odoo_category:
            data = {
                "name": odoo_category.display_name,
            }
        if instance.ks_update_mapped_category:
            data = {
                "name": json_data.get('name'),
            }
        if not json_data.get("parent"):
            data.update({"parent_id": False})
        return data

    def ks_map_product_category_data_for_layer(self, json_data, odoo_category, instance):
        data = {
            'ks_slug': json_data.get("slug", ''),
            'ks_wc_instance': instance.id,
            'ks_woo_category_id': json_data.get("id"),
            'ks_product_category': odoo_category.id,
            'ks_description': json_data.get("description", '')
        }
        return data

    def ks_map_prepare_data_for_layer(self, instance, product_category):
        """
        :param product_category: product.category()
        :param instance: ks.woo.connector.instance()
        :return: layer compatible data
        """
        data = {
            "ks_product_category": product_category.id,
            "ks_wc_instance": instance.id,
        }
        return data


class KsProductCategoryExtended(models.Model):
    _inherit = 'product.category'

    ks_product_category = fields.One2many('ks.woo.product.category', 'ks_product_category')

    def action_woo_layer_categories(self):
        """
        opens wizard fot woo layer categories
        :return: action
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("ks_woocommerce.action_ks_woo_product_category")
        action['domain'] = [('id', 'in', self.ks_product_category.ids)]
        return action

    def ks_push_to_woocommerce(self):
        if self:
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_push').read()[0]
                action['context'] = {'push_to_woo': True}
                return action
            else:
                data_prepared = self.ks_product_category.filtered(lambda x: x.ks_wc_instance.id == instances.id)
                if data_prepared:
                    ##Run update woo record command here
                    self.env['ks.woo.product.category'].update_woo_record(instances, self, export_to_woo=True)
                else:
                    self.env['ks.woo.product.category'].create_woo_record(instances, self, export_to_woo=True)
        else:
            active_ids = self.env.context.get("active_ids")
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_push').read()[0]
                action['context'] = {'push_to_woo': True, 'active_ids': active_ids, 'active_model': 'res.partner'}
                return action
            else:
                records = self.browse(active_ids)
                if len(records) == 1:
                    data_prepared = records.ks_product_category.filtered(lambda x: x.ks_wc_instance.id == instances.id)
                    if data_prepared:
                        ##Run update woo record command here
                        self.env['ks.woo.product.category'].update_woo_record(instances, records, export_to_woo=True)
                    else:
                        self.env['ks.woo.product.category'].create_woo_record(instances, records, export_to_woo=True)
                else:
                    for rec in records:
                        data_prepared = rec.ks_product_category.filtered(
                            lambda x: x.ks_wc_instance.id == instances.id)
                        if data_prepared:
                            self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instances,
                                                                                            'ks.woo.product.category',
                                                                                            'product.category', rec.id,
                                                                                            'update', True, True)
                        else:
                            self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instances,
                                                                                            'ks.woo.product.category',
                                                                                            'product.category', rec.id,
                                                                                            'create', True, True)
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_pull_from_woocommerce(self):
        if self:
            instance_counts = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instance_counts) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_pull').read()[0]
                action['context'] = {'pull_from_woo': True}
                return action
            else:
                data_prepared = self.ks_product_category.filtered(lambda x: x.ks_wc_instance.id == instance_counts.id)
                if data_prepared and data_prepared.ks_woo_category_id:
                    ##Handle woo import here
                    woo_id = data_prepared.ks_woo_category_id
                    json_data = self.env['ks.woo.product.category'].ks_woo_get_category(woo_id,
                                                                                        instance=instance_counts)
                    if json_data:
                        category = self.env['ks.woo.product.category'].ks_manage_catgeory_import(instance_counts,
                                                                                                 json_data)
                    else:
                        _logger.info("Fatal Error in Syncing Category from woocommerce")

                else:
                    _logger.info("Layer record must have woo id")
        else:
            active_ids = self.env.context.get("active_ids")
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_pull').read()[0]
                action['context'] = {'pull_from_woo': True, 'active_ids': active_ids,
                                     'active_model': 'product.category'}
                return action
            else:
                records = self.browse(active_ids)
                if len(records) == 1:
                    data_prepared = records.ks_product_category.filtered(
                        lambda x: x.ks_wc_instance.id == instances.id)
                    if data_prepared and data_prepared.ks_woo_category_id:
                        ##Handle woo import here
                        woo_id = data_prepared.ks_woo_category_id
                        json_data = self.env['ks.woo.product.category'].ks_woo_get_category(woo_id,
                                                                                            instance=instances)
                        if json_data:
                            category = self.env['ks.woo.product.category'].ks_manage_catgeory_import(instances,
                                                                                                     json_data)
                        else:
                            _logger.info("Fatal Error in Syncing Category from woocommerce")

                    else:
                        _logger.info("Layer record must have woo id")
                else:
                    for rec in records:
                        data_prepared = rec.ks_product_category.filtered(
                            lambda x: x.ks_wc_instance.id == instances.id)
                        if data_prepared and data_prepared.ks_woo_category_id:
                            ##Handle woo import here
                            woo_id = data_prepared.ks_woo_category_id
                            json_data = self.env['ks.woo.product.category'].ks_woo_get_category(woo_id,
                                                                                                instance=instances)
                            if json_data:
                                self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(instance=instances,
                                                                                                 data=[json_data])
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_manage_direct_syncing(self, record, instance_ids, push=False, pull=False):
        try:
            if len(record) == 1:
                for instance in instance_ids:
                    if push:
                        data_prepared = record.ks_product_category.filtered(
                            lambda x: x.ks_wc_instance.id == instance.id)
                        if data_prepared:
                            ##Run update woo record command here
                            self.env['ks.woo.product.category'].update_woo_record(instance, record, export_to_woo=True)
                        else:
                            self.env['ks.woo.product.category'].create_woo_record(instance, record, export_to_woo=True)

                    elif pull:
                        ##Handling of pull ther records from woocommerce here
                        data_prepared = record.ks_product_category.filtered(
                            lambda x: x.ks_wc_instance.id == instance.id)
                        if data_prepared and data_prepared.ks_woo_category_id:
                            ##Handle woo import here
                            woo_id = data_prepared.ks_woo_category_id
                            json_data = self.env['ks.woo.product.category'].ks_woo_get_category(woo_id,
                                                                                                instance=instance)
                            if json_data:
                                category = self.env['ks.woo.product.category'].ks_manage_catgeory_import(instance,
                                                                                                         json_data)
                            else:
                                _logger.info("Fatal Error in Syncing Category from woocommerce")

                        else:
                            _logger.info("Layer record must have woo id")
            else:
                for instance in instance_ids:
                    if push:
                        for rec in record:
                            data_prepared = rec.ks_product_category.filtered(
                                lambda x: x.ks_wc_instance.id == instance.id)
                            if data_prepared:
                                self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instance,
                                                                                                'ks.woo.product.category',
                                                                                                'product.category',
                                                                                                rec.id,
                                                                                                'update', True, True)
                            else:
                                self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instance,
                                                                                                'ks.woo.product.category',
                                                                                                'product.category',
                                                                                                rec.id,
                                                                                                'create', True, True)
                    elif pull:
                        for rec in record:
                            data_prepared = rec.ks_product_category.filtered(
                                lambda x: x.ks_wc_instance.id == instance.id)
                            if data_prepared and data_prepared.ks_woo_category_id:
                                ##Handle woo import here
                                woo_id = data_prepared.ks_woo_category_id
                                json_data = self.env['ks.woo.product.category'].ks_woo_get_category(woo_id,
                                                                                                    instance=instance)
                                if json_data:
                                    self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(instance=instance,
                                                                                                     data=[json_data])


        except Exception as e:
            _logger.info(str(e))


    def open_mapper(self):
        """
        opens mapper wizard to map category
        :return: mapped
        """
        active_records = self._context.get("active_ids", False)
        model = self.env['ir.model'].search([('model', '=', self._name)])
        mapped = self.env['ks.global.record.mapping'].action_open_category_mapping_wizard(model,
                                                                                          active_records,
                                                                                          "Category Record Mapping")
        return mapped

    def write(self, values):
        for rec in self:
            ks_woo_product_cat = self.env['ks.woo.product.category'].search([('ks_product_category', '=', rec.id)])
            for woo_categ in ks_woo_product_cat:
                if woo_categ.ks_woo_category_id:
                    woo_categ.update({'ks_sync_date': datetime.datetime.now()})

        return super(KsProductCategoryExtended, self).write(values)