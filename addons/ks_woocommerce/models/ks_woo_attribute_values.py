# -*- coding: utf-8 -*-

from odoo import fields, models, _
import logging
_logger = logging.getLogger(__name__)


class KsProductAttributeValueExtended(models.Model):
    _inherit = "product.attribute.value"

    ks_connected_woo_attribute_terms = fields.One2many('ks.woo.pro.attr.value', 'ks_pro_attr_value',
                                                       string="Woo Attribute Values Ids")


class KsWooProductAttributeModel(models.Model):
    _name = "ks.woo.pro.attr.value"
    _rec_name = "ks_name"
    _description = "Woo Product Attribute Value"

    ks_slug = fields.Char(string="Slug", help="Displays WooCommerce Attribute Value Slug Name")
    ks_attribute_id = fields.Many2one('product.attribute', string="Attribute", ondelete='cascade',
                                      related='ks_pro_attr_value.attribute_id',
                                      index=True,
                                      help="The attribute cannot be changed once the value is used on at least one "
                                           "product.")
    ks_woo_attribute_id = fields.Integer('Woo Attribute ID', readonly=True,
                                         help=_("the record id of the particular record defied in the Connector"))
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", readonly=True,
                                     help=_("WooCommerce Connector Instance reference"),
                                     ondelete='cascade')
    ks_woo_attribute_term_id = fields.Char('Woo Attribute Term ID', readonly=True, help="Displays Attribute Value WooCommerce ID")
    ks_pro_attr_value = fields.Many2one('product.attribute.value', string="Odoo Attribute Value", ondelete='cascade', help="Displays Odoo Attribute Value Name Reference")
    ks_name = fields.Char(string='Value', related="ks_pro_attr_value.name", translate=True, help="Displays WooCommerce Attribute Value Name")
    ks_mapped = fields.Boolean(string = "Manual Mapping", readonly = True)

    def ks_manage_value_preparation(self, instance, attribute_values):
        for value in attribute_values:
            product_attr_value_exist = self.check_if_already_prepared(instance, value)
            if not product_attr_value_exist:
                self.create_woo_record(instance, value)
            else:
                self.update_woo_record(instance, value)

    def ks_map_prepare_data_for_layer(self, instance, product_attribute_value):
        """
        """
        data = {
            "ks_pro_attr_value": product_attribute_value.id,
            "ks_wc_instance": instance.id,
            "ks_attribute_id": product_attribute_value.attribute_id.id
        }
        return data

    def create_woo_record(self, instance, attribute_value):
        """
        Created woo data in layer model woo to odoo
        :param instance: Woocommerce Instance
        :param attribute_value: attribute value model domain
        :return:
        """
        data = self.ks_map_prepare_data_for_layer(instance, attribute_value)
        try:
            woo_attribute_term = self.create(data)
            return woo_attribute_term
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                   status="failed",
                                                                   type="attribute_value",
                                                                   instance=instance,
                                                                   odoo_model="product.attribute.value",
                                                                   layer_model="ks.woo.pro.attr.value",
                                                                   id=attribute_value.id,
                                                                   message=str(e))

    def update_woo_record(self, instance, attribute_value):
        """
        Updates layer model record with attribute data from woo
        :param instance: Woocommerce Instances
        :param attribute_value: attribute value model domain
        :return:
        """
        data = self.ks_map_prepare_data_for_layer(instance, attribute_value)
        try:
            product_attr_value_exist = self.check_if_already_prepared(instance, attribute_value)
            if product_attr_value_exist:
                product_attr_value_exist.write(data)
                return product_attr_value_exist
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                   status="failed",
                                                                   type="attribute_value",
                                                                   instance=instance,
                                                                   odoo_model="product.attribute.value",
                                                                   layer_model="ks.woo.pro.attr.value",
                                                                   id=attribute_value.id,
                                                                   message=str(e))

    def update_record_data_in_odoo(self):
        """
        Use: This will update the Layer record data to The Main Attribute linked to it
        :return:
        """
        for rec in self:
            try:
                json_data = rec.ks_pro_attr_value.ks_map_odoo_attribute_term_data_to_update(rec)
                rec.ks_pro_attr_value.write(json_data)
                rec.ks_need_update = False
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param('update', 'attribute_value', rec.ks_wc_instance,
                                                              rec.ks_attribute_id.id, 'Failed due to',
                                                              rec.ks_woo_attribute_id, 'wl_to_odoo',
                                                              'failed', 'product.attribute.value',
                                                              'ks.woo.pro.attr.value', e)

    def ks_populate_layer_update_to_odoo(self):
        """
        Use: This will check the No of instance in the main record if single record exist then it will update directly
        :return: None
        """
        self.ks_need_update = True
        if len(self.ks_wc_instance) == 1:
            self.update_record_data_in_odoo()

    def check_if_already_prepared(self, instance, product_attr_value):
        """
        Checks if the records are already prepared or not
        :param instance: Woocommerce Instances
        :param product_attr_value: Product attribute value layer model domain
        :return: product_attr_value domain
        """
        product_attr_value_exist = self.search([('ks_wc_instance', '=', instance.id),
                                                ('ks_pro_attr_value', '=', product_attr_value.id)], limit=1)
        return product_attr_value_exist

    def ks_woo_export_attribute_terms(self, attribute_id):
        """
        Use: This will export the selected new records from Odoo to WooCommerce and then store the response
        :attribute_id: Id of woo attribute to be created
        :return: None
        """
        for record in self:
            try:
                woo_instance = record.ks_wc_instance
                json_data = record.ks_prepare_export_json_data()
                if woo_instance and not record.ks_woo_attribute_term_id:
                    attribute_term_data = self.ks_woo_post_attribute_term(json_data, attribute_id, woo_instance)
                    if attribute_term_data:
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(attribute_term_data, record,
                                                                                         'ks_woo_attribute_term_id',
                                                                                         {
                                                                                             "ks_slug": attribute_term_data.get(
                                                                                                 'slug') or ''}
                                                                                         )
                        record.ks_woo_attribute_id = attribute_id
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param('create', 'attribute_value', record.ks_wc_instance.id,
                                                              record.ks_attribute_id.id, 'Failed due to',
                                                              record.ks_woo_attribute_id, 'wl_to_woo',
                                                              'failed', 'product.attribute.value',
                                                              'ks.woo.pro.attr.value', e)

    def ks_woo_update_attribute_terms(self, attribute_id):
        """
        Use: This will update the selected records from Odoo to WooCommerce and then store the response
        :attribute_id: Id of woo attribute to be created
        :return: None
        """
        for record in self:
            try:
                woo_instance = record.ks_wc_instance
                json_data = record.ks_prepare_export_json_data()
                if woo_instance and record.ks_woo_attribute_term_id:
                    attribute_term_data = self.ks_woo_update_attribute_term(attribute_id,
                                                                            record.ks_woo_attribute_term_id,json_data,
                                                                            woo_instance)
                    if attribute_term_data:
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(attribute_term_data, record,
                                                                                         'ks_woo_attribute_term_id',
                                                                                         {
                                                                                             "ks_slug": attribute_term_data.get(
                                                                                                 'slug') or ''}
                                                                                         )
                        record.ks_woo_attribute_id = attribute_id
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param('update', 'attribute_value', record.ks_wc_instance.id,
                                                              record.ks_attribute_id.id, 'Failed due to',
                                                              record.ks_woo_attribute_id, 'wl_to_woo',
                                                              'failed', 'product.attribute.value',
                                                              'ks.woo.pro.attr.value', e)

    def ks_woo_import_attribute_terms(self):
        """
        Imports and update the attributes terms from woo to odoo
        :return:
        """
        for record in self:
            try:
                woo_instance = record.ks_wc_instance
                if woo_instance and record.ks_woo_attribute_term_id and record.ks_woo_attribute_id:
                    attribute_term_data = self.ks_woo_get_attribute_term(record.ks_woo_attribute_id,
                                                                         record.ks_woo_attribute_term_id, woo_instance)
                    if attribute_term_data:
                        json_data = record.ks_prepare_import_json_data(attribute_term_data, record.ks_woo_attribute_id)
                        record.write(json_data)
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(attribute_term_data, record,
                                                                                         'ks_woo_attribute_term_id',
                                                                                         {
                                                                                             "ks_slug": attribute_term_data.get(
                                                                                                 'slug') or ''}
                                                                                         )
                        record.ks_populate_layer_update_to_odoo()
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param('update', 'attribute', record.ks_wc_instance.id,
                                                              record.ks_attribute_id.id, 'Failed due to',
                                                              record.ks_woo_attribute_id, 'woo_to_odoo',
                                                              'failed', 'product.attribute.value',
                                                              'ks.woo.pro.attr.value', e)

    def ks_woo_get_all_attribute_terms(self, instance_id, attribute_id):
        """
        Gets all the attribute value from woo to odoo
        :param instance_id: Woocommerce Instance
        :param attribute_id: Id of attribute to fetch from woocommerce
        :return: json data response
        """
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = []
        try:
            wc_api = instance_id.ks_woo_api_authentication()
            while multi_api_call:
                attribute_term_response = wc_api.get("products/attributes/%s/terms" % attribute_id,
                                                     params={'per_page': per_page, 'page': page})
                if attribute_term_response.status_code in [200, 201]:
                    all_retrieved_data.extend(attribute_term_response.json())
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="attribute_value",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance_id,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.pro.attr.value",
                                                                       message=str(attribute_term_response.text))
                total_api_calls = attribute_term_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="attribute_value",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance_id,
                                                               woo_id=0,
                                                               layer_model="ks.woo.pro.attr.value",
                                                               message="Fetch of Product is successful")
            return all_retrieved_data
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="attribute_value",
                                                               instance=instance_id,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.pro.attr.value",
                                                               message=str(e))
    def ks_woo_get_attribute_term(self, attribute_id, attribute_val_id, instance_id):
        """
        Gets a single attribute value from woo to odoo
        :param attribute_id: Id of woo attribute
        :param attribute_val_id: Id of woo attribute value
        :param instance_id: Woocommerce Instance
        :return: json data response
        """
        try:
            wc_api = instance_id.ks_woo_api_authentication()
            woo_attribute_term_response = wc_api.get(
                "products/attributes/%s/terms/%s" % (attribute_id, attribute_val_id))
            if woo_attribute_term_response.status_code in [200, 201]:
                attribute_term_data = woo_attribute_term_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="attribute_value",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance_id,
                                                                   woo_id=attribute_term_data.get("id"),
                                                                   layer_model="ks.woo.pro.attr.value",
                                                                   message="Fetch of Attribute Value successful")
                return attribute_term_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="attribute_value",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.pro.attr.value",
                                                                   message=str(woo_attribute_term_response.text))
                return False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="attribute_value",
                                                               instance=instance_id,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.pro.attr.value",
                                                               message=str(e))

    def ks_woo_post_attribute_term(self, data, attribute_id, instance_id):
        """
        Create an attribute value on woo
        :param data: json data to create attribute values
        :param attribute_id: Id of attributes
        :param instance_id: Woocommerce Instances
        :return: json data response
        """
        try:
            wc_api = instance_id.ks_woo_api_authentication()
            woo_attribute_term_response = wc_api.post("products/attributes/%s/terms" % attribute_id, data)
            if woo_attribute_term_response.status_code in [200, 201]:
                attribute_term_data = woo_attribute_term_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="attribute_value",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance_id,
                                                                   woo_id=attribute_term_data.get("id"),
                                                                   layer_model="ks.woo.pro.attr.value",
                                                                   message="Create of Attribute Value successful")
                return attribute_term_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="attribute_value",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.pro.attr.value",
                                                                   message=str(woo_attribute_term_response.text))
        except ConnectionError:
            raise Exception(
                "Couldn't Connect the Instance at time of attribute_value Syncing !! Please check the network "
                "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="attribute_value",
                                                               instance=instance_id,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.pro.attr.value",
                                                               message=str(e))

    def ks_woo_update_attribute_term(self, attribute_id, attribute_val_id, data, instance_id):
        """
        Update Attribute values on woocommerce
        :param attribute_id: Id of attribute to update
        :param attribute_val_id: Id of attribute value to update
        :param data: data to update attribute value
        :param instance_id: woocommrece instance
        :return: json data response
        """
        try:
            wc_api = instance_id.ks_woo_api_authentication()
            woo_attribute_term_response = wc_api.put(
                "products/attributes/%s/terms/%s" % (attribute_id, attribute_val_id),
                data)
            if woo_attribute_term_response.status_code in [200, 201]:
                attribute_term_data = woo_attribute_term_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_post",
                                                                   status="success",
                                                                   type="attribute_value",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance_id,
                                                                   woo_id=attribute_term_data.get("id"),
                                                                   layer_model="ks.woo.pro.attr.value",
                                                                   message="Update of Attribute Value successful")
                return attribute_term_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="attribute_value",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.pro.attr.value",
                                                                   message=str(woo_attribute_term_response.text))
        except ConnectionError:
            raise Exception(
                "Couldn't Connect the Instance at time of attribute_value Syncing !! Please check the network "
                "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="attribute_value",
                                                               instance=instance_id,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.pro.attr.value",
                                                               message=str(e))

    def ks_prepare_import_json_data(self, json_data, attribute_id):
        """
        Prepares data to be imported on odoo from woo
        :param json_data: api json data from woo
        :param attribute_id: id of attribute
        :return: json data
        """
        data = {
            "ks_name": json_data.get('name'),
            "ks_slug": json_data.get('slug') or '',
            "ks_woo_attribute_id": attribute_id
        }
        return data

    def ks_manage_attribute_value_import(self, woo_instance, woo_attribute_id, odoo_attribute, attribute_values, queue_record=False):
        try:
            for value_data in attribute_values:
                layer_attribute_value = self.search([('ks_wc_instance', '=', woo_instance.id),
                                                     ("ks_attribute_id", '=', odoo_attribute.id),
                                                     ("ks_woo_attribute_term_id", '=', value_data.get('id'))])
                odoo_attribute_value = layer_attribute_value.ks_pro_attr_value
                odoo_main_data = self.ks_map_attribute_value_data_for_odoo(value_data, odoo_attribute.id)
                if layer_attribute_value:
                    odoo_attribute_value.ks_manage_attribute_value_in_odoo(odoo_main_data.get('name'),
                                                                           odoo_attribute.id,
                                                                           odoo_attribute_value=odoo_attribute_value)
                    layer_data = self.ks_map_attribute_value_data_for_layer(value_data, odoo_attribute, odoo_attribute_value, woo_attribute_id, woo_instance)
                    layer_attribute_value.write(layer_data)
                else:
                    odoo_attribute_value = odoo_attribute_value.ks_manage_attribute_value_in_odoo(odoo_main_data.get('name'),
                                                                                                  odoo_attribute.id,
                                                                                                  odoo_attribute_value=odoo_attribute_value)
                    layer_data = self.ks_map_attribute_value_data_for_layer(value_data,
                                                                            odoo_attribute,
                                                                            odoo_attribute_value, woo_attribute_id, woo_instance)
                    layer_attribute_value = self.create(layer_data)
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            _logger.info(str(e))

    def ks_map_attribute_value_data_for_odoo(self, value_data, attribute_id):
        data = {
            "name": value_data.get("name"),
            "display_type": 'select',
            "attribute_id": attribute_id
        }
        return data

    def ks_prepare_export_json_data(self, odoo_attribute_value):
        """
        Prepares to export json data from odoo to woo
        :return: woo compatible data
        """
        data = {
            "name": odoo_attribute_value.name,
            "slug": self.ks_slug if self.ks_slug else '',
        }
        return data

    def ks_manage_attribute_value_export(self, attribute_id, queue_record=False):
        """
        :param queue_record: Queue Boolean Trigger
        :return: json response
        """
        try:
            for attribute_value in self:
                odoo_base_attribute_value = attribute_value.ks_pro_attr_value
                woo_attribute_id = attribute_value.ks_woo_attribute_id or attribute_id
                woo_attribute_value_id = attribute_value.ks_woo_attribute_term_id
                woo_attribute_data = attribute_value.ks_prepare_export_json_data(odoo_base_attribute_value)
                if woo_attribute_value_id:
                    woo_attribute_value_data_response = attribute_value.ks_woo_update_attribute_term(woo_attribute_id,
                                                                                          woo_attribute_value_id,
                                                                                          woo_attribute_data,
                                                                                          self.ks_wc_instance)
                else:
                    woo_attribute_value_data_response = attribute_value.ks_woo_post_attribute_term(woo_attribute_data,woo_attribute_id,

                                                                                   self.ks_wc_instance)
                if woo_attribute_value_data_response:
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(woo_attribute_value_data_response,
                                                                                     attribute_value,
                                                                                     'ks_woo_attribute_term_id',
                                                                                     {
                                                                                         "ks_slug": woo_attribute_value_data_response.get(
                                                                                             'slug') or '',
                                                                                         "ks_woo_attribute_id": woo_attribute_id}
                                                                                     )
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()

    def ks_map_attribute_value_data_for_layer(self, value_data, odoo_attribute, odoo_attribute_value, woo_attribute_id, woo_instance):
        data = {
                "ks_name": value_data.get('name'),
                "ks_slug": value_data.get('slug') or '',
                "ks_woo_attribute_id": woo_attribute_id,
                "ks_attribute_id": odoo_attribute.id,
                "ks_wc_instance": woo_instance.id,
                "ks_pro_attr_value": odoo_attribute_value.id,
                "ks_woo_attribute_term_id": value_data.get('id')

            }
        return data
