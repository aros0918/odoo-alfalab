# -*- coding: utf-8 -*-

import datetime

from odoo import models, fields, _


class KsProductTag(models.Model):
    _name = 'ks.woo.product.tag'
    _description = 'WooCommerce Tags'
    _rec_name = 'ks_name'

    ks_name = fields.Char('Name', required=True, help="Displays Tag Name")
    ks_woo_tag_id = fields.Integer('Woo Tag Id', readonly=True, help="Displays WooCommerce Tag ID")
    ks_slug = fields.Char('Slug', help="Displays Tag Slug")
    ks_description = fields.Text(string='Description')
    ks_wc_instance = fields.Many2one('ks.woo.connector.instance', string='Instance', required=True,
                                     ondelete='cascade', help="Displays WooCommerce Instance Name")
    ks_date_created = fields.Datetime('Date Created', help=_("The date on which the record is created on the Connected"
                                                             " Connector Instance"), readonly=True)
    ks_date_updated = fields.Datetime('Date Updated', help=_("The latest date on which the record is updated on the"
                                                             " Connected Connector Instance"), readonly=True)
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
            if rec.ks_woo_tag_id:
                values.update({'ks_sync_date': datetime.datetime.now()})
        super(KsProductTag, self).write(values)

    def ks_map_product_tag_data_to_create(self, instance, tag_json_data):
        """
        Prepare Woo Product Attribute Data for odoo to woo
        :param instance: woocommerce instance
        :param tag_json_data: api json data
        :return: json data
        """
        data = {
            'ks_name': tag_json_data.get('name'),
            'ks_slug': tag_json_data.get('slug'),
            'ks_description': tag_json_data.get('description'),
            'ks_wc_instance': instance.id
        }
        return data

    def create_woo_record(self, woo_instance, tag_data):
        """
        create woo record in data
        :param woo_instance: Woocommerce Instance
        :param tag_data: json data for tags
        :return: model record created domain
        """
        data = self.ks_map_product_tag_data_to_create(woo_instance, tag_data)
        try:
            woo_tag = self.create(data)
        except Exception as e:
            raise e
        else:
            return woo_tag

    def ks_woo_get_all_product_tag(self, instance, include=False):
        """
        This function will get all the category from WooCommerce
           :param instance:ks.woo.connector.instance()
           :param include: params for specific records and date filters
           :return: Dictionary of Created Woo category
        """
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = None
        if include:
            params = {'per_page': per_page,
                      'page': page,
                      'include': include}
        else:
            params = {'per_page': per_page, 'page': page}
        try:
            while multi_api_call:
                wc_api = instance.ks_woo_api_authentication()
                tag_data_response = wc_api.get("products/tags", params=params)
                if tag_data_response.status_code in [200, 201]:
                    all_retrieved_data = tag_data_response.json()
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="tags",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.product.tag",
                                                                       message=str(tag_data_response.text))
                total_api_calls = tag_data_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                    params.update({'page': page})
                else:
                    multi_api_call = False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="tags",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.tag",
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="tags",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance,
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.tag",
                                                               message="Fetch of Tags successful")
            return all_retrieved_data

    def ks_woo_get_product_tag(self, tag_id, instance):
        """
        Get specific product tag from woocommrece
        :param tag_id: Woocommerce Tag ID
        :param instance: woocommrece instance
        :return: json response
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            tag_data_response = wc_api.get("products/tags/%s" % tag_id)
            tag_data = False
            if tag_data_response.status_code in [200, 201]:
                tag_data = tag_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="tags",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=tag_data.get("id", 0),
                                                                   layer_model="ks.woo.product.tag",
                                                                   message="Fetch of Tags successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="tags",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.tag",
                                                                   message=str(tag_data_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="tags",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.tag",
                                                               message=str(e))
        else:
            return tag_data

    def ks_woo_post_product_tag(self, data, instance):
        """
        Function to create the product tags
        :param data: data to create the tag
        :param instance: woocommerce instance
        :return: json response
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            tag_data_response = wc_api.post("products/tags", data)
            tag_data = False
            if tag_data_response.status_code in [200, 201]:
                tag_data = tag_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="tags",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=tag_data.get("id", 0),
                                                                   layer_model="ks.woo.product.tag",
                                                                   message="Create of Tags successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="tags",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.tag",
                                                                   message=str(tag_data_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="tags",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.tag",
                                                               message=str(e))
        else:
            return tag_data

    def ks_woo_update_product_tag(self, tag_id, data, instance):
        """
        Function to update the product tags
        :param data: data to update the tag
        :param instance: woocommerce instance
        :return: json response
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            tag_response = wc_api.put("products/tags/%s" % tag_id, data)
            tag_data = False
            if tag_response.status_code in [200, 201]:
                tag_data = tag_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_post",
                                                                   status="success",
                                                                   type="tags",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=tag_data.get("id", 0),
                                                                   layer_model="ks.woo.product.tag",
                                                                   message="Update of Tags successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="tags",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.tag",
                                                                   message=str(tag_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="tags",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.tag",
                                                               message=str(e))
        else:
            return tag_data

    def ks_woo_import_product_tags(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance and e.ks_woo_tag_id)
                if len(records):
                    for dat in records:
                        json_data = [self.ks_woo_get_product_tag(dat.ks_woo_tag_id, dat.ks_wc_instance)]
                        if json_data[0]:
                            self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(data=json_data,
                                                                                        instance=dat.ks_wc_instance)
                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Tags Records enqueued in Queue 
                                                                           Please refer Queue and logs for further details
                                                                           ''')
            except Exception as e:
                raise e
        else:
            try:
                self.ensure_one()
                json_data = self.ks_woo_get_product_tag(self.ks_woo_tag_id, self.ks_wc_instance)
                if json_data:
                    self.ks_woo_import_product_tag_update(json_data, self.ks_wc_instance)
                return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                       "Action Performed. Please refer logs for further details.")
            except Exception as e:
                raise e

    def ks_woo_export_product_tags(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance)
                self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(records=records)
                return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Tags Records enqueued in Queue 
                                                                           Please refer Queue and logs for further details
                                                                           ''')
            except Exception as e:
                raise e
        else:
            try:
                self.ensure_one()
                if self.ks_woo_tag_id and self.ks_wc_instance:
                    self.ks_update_tag_odoo_to_woo()
                elif not self.ks_woo_tag_id and self.ks_wc_instance:
                    tags = self.ks_create_tag_odoo_to_woo()
                return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                       "Action Performed. Please refer logs for further details.")

            except Exception as e:
                raise e

    def ks_manage_woo_product_tag_import(self, woo_instance, tag_data, queue_record=False):
        """
        Main method to handle create and update of tag on  model
        :param woo_instance: Woocommerce Instance
        :param tag_data: api json data for tag
        :param queue_record: record reference for queue
        :return: model domain
        """
        try:
            tag_exist = self.env['ks.woo.product.tag'].search([
                ('ks_woo_tag_id', '=', tag_data.get("id", '')),
                ('ks_wc_instance', '=', woo_instance.id)])
            if not tag_exist:
                woo_tag = self.create_woo_record(woo_instance, tag_data)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(tag_data, woo_tag,
                                                                                 'ks_woo_tag_id')
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                   ks_woo_id=tag_data.get("id", 0),
                                                                   ks_model="ks.woo.product.tag",
                                                                   ks_layer_model="ks.woo.product.tag",
                                                                   ks_status="success",
                                                                   ks_woo_instance=woo_instance,
                                                                   ks_record_id=woo_tag.id,
                                                                   ks_message="Import create of tags successful",
                                                                   ks_type="tags",
                                                                   ks_operation_flow="woo_to_odoo")
                woo_tag.ks_sync_date = datetime.datetime.now()
                woo_tag.ks_last_exported_date = woo_tag.ks_sync_date
                woo_tag.sync_update()
                return woo_tag
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                               ks_woo_id=tag_data.get("id", 0),
                                                               ks_model="ks.woo.product.tag",
                                                               ks_layer_model="ks.woo.product.tag",
                                                               ks_status="failed",
                                                               ks_woo_instance=woo_instance,
                                                               ks_record_id=0,
                                                               ks_message=str(e),
                                                               ks_type="tags",
                                                               ks_operation_flow="woo_to_odoo")

    def ks_woo_import_product_tag_update(self, tag_data, instance, queue_record=False):
        """
        Import product tag from woo to odoo by updating it
        :param tag_data: json data
        :param queue_record: queue record domain
        """
        try:
            json_data = self.ks_prepare_import_json_data(tag_data, instance)
            if tag_data:
                self.write(json_data)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(tag_data, self,
                                                                                 'ks_woo_tag_id')
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                   ks_woo_id=tag_data.get("id", 0),
                                                                   ks_model="ks.woo.product.tag",
                                                                   ks_layer_model="ks.woo.product.tag",
                                                                   ks_status="success",
                                                                   ks_woo_instance=instance,
                                                                   ks_record_id=self.id,
                                                                   ks_message="Import update of Tag successful",
                                                                   ks_type="tags",
                                                                   ks_operation_flow="woo_to_odoo")
                self.ks_sync_date = datetime.datetime.now()
                self.ks_last_exported_date = self.ks_sync_date
                self.sync_update()
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                               ks_woo_id=tag_data.get("id", 0),
                                                               ks_model="ks.woo.product.tag",
                                                               ks_layer_model="ks.woo.product.tag",
                                                               ks_status="failed",
                                                               ks_woo_instance=instance,
                                                               ks_record_id=self.id,
                                                               ks_message=str(e),
                                                               ks_type="tags",
                                                               ks_operation_flow="woo_to_odoo")

    def ks_create_tag_odoo_to_woo(self, queue_record=False):
        """
        create tag from odoo model to woo
        :param queue_record: record reference for queue
        :return: json data response from api
        """
        woo_instance = False
        try:
            woo_instance = self.ks_wc_instance
            json_data = self.ks_prepare_export_json_data()
            if woo_instance and not self.ks_woo_tag_id:
                tag_data = self.ks_woo_post_product_tag(json_data, woo_instance)
                if tag_data:
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(tag_data, self,
                                                                                     'ks_woo_tag_id',
                                                                                     {"ks_slug": tag_data.get(
                                                                                         'slug') or ''})
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_woo",
                                                                       ks_woo_id=tag_data.get("id", 0),
                                                                       ks_model="ks.woo.product.tag",
                                                                       ks_layer_model="ks.woo.product.tag",
                                                                       ks_status="success",
                                                                       ks_woo_instance=woo_instance,
                                                                       ks_record_id=self.id,
                                                                       ks_message="Export create of Tag successful",
                                                                       ks_type="tags",
                                                                       ks_operation_flow="odoo_to_woo")
                    self.ks_sync_date = datetime.datetime.now()
                    self.ks_last_exported_date = self.ks_sync_date
                    self.sync_update()
                    return tag_data
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                   ks_woo_id=0,
                                                                   ks_model="ks.woo.product.tag",
                                                                   ks_layer_model="ks.woo.product.tag",
                                                                   ks_status="failed",
                                                                   ks_woo_instance=woo_instance,
                                                                   ks_record_id=self.id,
                                                                   ks_message=str(e),
                                                                   ks_type="tags",
                                                                   ks_operation_flow="odoo_to_woo")

    def ks_update_tag_odoo_to_woo(self, queue_record=False):
        """
        Updates the odoo model record on woo
        param queue_record: record reference for queue
        """
        woo_instance = False
        try:
            woo_instance = self.ks_wc_instance
            json_data = self.ks_prepare_export_json_data()
            if woo_instance and self.ks_woo_tag_id:
                tag_data = self.ks_woo_update_product_tag(self.ks_woo_tag_id, json_data, woo_instance)
                if tag_data:
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(tag_data, self,
                                                                                     'ks_woo_tag_id',
                                                                                     {"ks_slug": tag_data.get(
                                                                                         'slug') or ''})
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_woo",
                                                                       ks_woo_id=tag_data.get("id", 0),
                                                                       ks_model="ks.woo.product.tag",
                                                                       ks_layer_model="ks.woo.product.tag",
                                                                       ks_status="success",
                                                                       ks_woo_instance=woo_instance,
                                                                       ks_record_id=self.id,
                                                                       ks_message="Export update of Tag successful",
                                                                       ks_type="tags",
                                                                       ks_operation_flow="odoo_to_woo")
                    self.ks_sync_date = datetime.datetime.now()
                    self.ks_last_exported_date = self.ks_sync_date
                    self.sync_update()
                return tag_data
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                               ks_woo_id=0,
                                                               ks_model="ks.woo.product.tag",
                                                               ks_layer_model="ks.woo.product.tag",
                                                               ks_status="failed",
                                                               ks_woo_instance=woo_instance,
                                                               ks_record_id=self.id,
                                                               ks_message=str(e),
                                                               ks_type="tags",
                                                               ks_operation_flow="odoo_to_woo")

    def ks_prepare_import_json_data(self, tag_json_data, instance):
        """
        Prepares json data for odoo model
        :param tag_json_data: api json data
        :return: odoo model compatible data
        """
        data = {
            'ks_name': tag_json_data.get('name'),
            'ks_slug': tag_json_data.get('slug'),
            'ks_description': tag_json_data.get('description'),
            'ks_wc_instance': instance.id
        }
        return data

    def ks_prepare_export_json_data(self):
        """
        Prepares json data for woocommerce
        :return: woo compatible json data
        """
        data = {
            'name': self.ks_name if self.ks_name else '',
            'slug': self.ks_slug if self.ks_slug else '',
            'description': self.ks_description if self.ks_description else '',
        }
        return data

    def ks_woo_export_product_tag(self):
        """
        Action server method to export records from odoo to woocommerce
        :return: None
        """
        if len(self) > 1:
            records = self.filtered(lambda e: not e.ks_woo_tag_id and e.ks_wc_instance)
            if len(records) > 0:
                self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(records=records)

                return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                       '''Product Tags Records enqueued in Queue 
                                                                       Please refer Queue and logs for further details
                                                                       ''')
        else:
            self.ensure_one()
            self.ks_create_tag_odoo_to_woo()
            return self.env['ks.message.wizard'].ks_pop_up_message("Done",
                                                                   '''Operation performed, Please refer Logs and Queues for 
                                                                   further Details.''')

    def ks_woo_update_product_tag_action(self):
        """
        Action server method to update records from odoo to woocommerce
        :return: ks.message.wizard() window
        """
        if len(self) > 1:
            records = self.filtered(lambda e: e.ks_woo_tag_id and e.ks_wc_instance)
            if len(records) > 0:
                self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(records=records)
                return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                       '''Product Tags Records enqueued in Queue 
                                                                       Please refer Queue and logs for further details
                                                                       ''')
        else:
            self.ensure_one()
            self.ks_update_tag_odoo_to_woo()
        return self.env['ks.message.wizard'].ks_pop_up_message("Done",
                                                               '''Operation performed, Please refer Logs and Queues for 
                                                               further Details.''')

    def ks_woo_import_product_tag(self):
        """
        Action server method to import records from woo to odoo
        :return: ks.message.wizard() window
        """
        tag_with_woo_id = self.filtered(lambda e: e.ks_woo_tag_id and e.ks_wc_instance)
        if len(tag_with_woo_id) > 1:
            all_woo_id = tag_with_woo_id.mapped('ks_woo_tag_id')
            specific_record_ids = ','.join(str(e) for e in all_woo_id)
            try:
                tag_response = self.ks_woo_get_all_product_tag(self.ks_wc_instance,
                                                               include=specific_record_ids)
                if tag_response:
                    self.env['ks.woo.queue.jobs'].ks_create_tag_record_in_queue(self.ks_wc_instance,
                                                                                data=tag_response)
                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Product Tags Records enqueued in Queue 
                                                                           Please refer Queue and logs for further details
                                                                           ''')
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param(ks_woo_instance=self.ks_wc_instance,
                                                              ks_operation_performed='fetch',
                                                              ks_type='system_status',
                                                              ks_record_id=0,
                                                              ks_woo_id=0,
                                                              ks_operation_flow='woo_to_odoo',
                                                              ks_status='failed',
                                                              ks_message="Tags Enqueue to queue jobs failed due to",
                                                              ks_error=e)

        else:
            self.ensure_one()
            if tag_with_woo_id:
                tag_data_response = self.ks_woo_get_product_tag(tag_with_woo_id.ks_woo_tag_id,
                                                                tag_with_woo_id.ks_wc_instance)
                if tag_data_response:
                    self.ks_woo_import_product_tag_update(tag_data_response, self.ks_wc_instance)
            return self.env['ks.message.wizard'].ks_pop_up_message("Done",
                                                                   '''Operation performed, Please refer Logs and Queues for 
                                                                   further Details.''')
