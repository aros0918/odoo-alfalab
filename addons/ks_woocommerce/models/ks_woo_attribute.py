# -*- coding: utf-8 -*-

import logging
import datetime

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class KsProductAttributeInherit(models.Model):
    _inherit = "product.attribute"

    ks_connected_woo_attributes = fields.One2many('ks.woo.product.attribute', 'ks_product_attribute',
                                                  string="Woo Attribute Ids")

    def action_woo_layer_attributes(self):
        """
        opens wizard fot woo layer attributes
        :return: action
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("ks_woocommerce.action_ks_woo_product_attribute")
        action['domain'] = [('id', 'in', self.ks_connected_woo_attributes.ids)]
        return action

    def ks_push_to_woocommerce(self):
        if self:
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_push').read()[0]
                action['context'] = {'push_to_woo': True}
                return action
            else:
                data_prepared = self.ks_connected_woo_attributes.filtered(lambda x: x.ks_wc_instance.id == instances.id)
                if data_prepared:
                    ##Run update woo record command here
                    self.env['ks.woo.product.attribute'].update_woo_record(instances, self, export_to_woo=True)
                else:
                    self.env['ks.woo.product.attribute'].create_woo_record(instances, self, export_to_woo=True)
        else:
            active_ids = self.env.context.get("active_ids")
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_push').read()[0]
                action['context'] = {'push_to_woo': True, 'active_ids': active_ids, 'active_model': 'product.attribute'}
                return action
            else:
                records = self.browse(active_ids)
                if len(records) == 1:
                    data_prepared = records.ks_connected_woo_attributes.filtered(
                        lambda x: x.ks_wc_instance.id == instances.id)
                    if data_prepared:
                        ##Run update woo record command here
                        self.env['ks.woo.product.attribute'].update_woo_record(instances, records, export_to_woo=True)
                    else:
                        self.env['ks.woo.product.attribute'].create_woo_record(instances, records, export_to_woo=True)
                else:
                    for rec in records:
                        data_prepared = rec.ks_connected_woo_attributes.filtered(
                            lambda x: x.ks_wc_instance.id == instances.id)
                        if data_prepared:
                            self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instances,
                                                                                            'ks.woo.product.attribute',
                                                                                            'product.attribute', rec.id,
                                                                                            'update', True, True)
                        else:
                            self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instances,
                                                                                            'ks.woo.product.attribute',
                                                                                            'product.attribute', rec.id,
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
                data_prepared = self.ks_connected_woo_attributes.filtered(
                    lambda x: x.ks_wc_instance.id == instance_counts.id)
                if data_prepared and data_prepared.ks_woo_attribute_id:
                    ##Handle woo import here
                    woo_id = data_prepared.ks_woo_attribute_id
                    json_data = self.env['ks.woo.product.attribute'].ks_woo_get_attribute(woo_id, instance_counts)
                    if json_data:
                        attributes = self.env['ks.woo.product.attribute'].ks_manage_attribute_import(instance_counts,
                                                                                                     json_data)
                    else:
                        _logger.info("Fatal Error in Syncing Attributes and its values from woocommerce")

                else:
                    _logger.info("Layer record must have woo id")
        else:
            active_ids = self.env.context.get("active_ids")
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_pull').read()[0]
                action['context'] = {'pull_from_woo': True, 'active_ids': active_ids,
                                     'active_model': 'product.attribute'}
                return action
            else:
                records = self.browse(active_ids)
                if len(records) == 1:
                    data_prepared = records.ks_connected_woo_attributes.filtered(
                        lambda x: x.ks_wc_instance.id == instances.id)
                    if data_prepared and data_prepared.ks_woo_attribute_id:
                        ##Handle woo import here
                        woo_id = data_prepared.ks_woo_attribute_id
                        json_data = self.env['ks.woo.product.attribute'].ks_woo_get_attribute(woo_id, instances)
                        if json_data:
                            attributes = self.env['ks.woo.product.attribute'].ks_manage_attribute_import(instances,
                                                                                                         json_data)
                        else:
                            _logger.info("Fatal Error in Syncing Attributes and its values from woocommerce")
                else:
                    for rec in records:
                        data_prepared = rec.ks_connected_woo_attributes.filtered(
                            lambda x: x.ks_wc_instance.id == instances.id)
                        woo_id = data_prepared.ks_woo_attribute_id
                        json_data = self.env['ks.woo.product.attribute'].ks_woo_get_attribute(woo_id, instances)
                        if json_data:
                            self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(
                                instance=instances,
                                data=[json_data])
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_manage_direct_syncing(self, record, instance_ids, push=False, pull=False):
        try:
            if len(record) == 1:
                for instance in instance_ids:
                    if push:
                        data_prepared = record.ks_connected_woo_attributes.filtered(
                            lambda x: x.ks_wc_instance.id == instance.id)
                        if data_prepared:
                            ##Run update woo record command here
                            self.env['ks.woo.product.attribute'].update_woo_record(instance, record, export_to_woo=True)
                        else:
                            self.env['ks.woo.product.attribute'].create_woo_record(instance, record, export_to_woo=True)

                    elif pull:
                        ##Handling of pull ther records from woocommerce here
                        data_prepared = record.ks_connected_woo_attributes.filtered(
                            lambda x: x.ks_wc_instance.id == instance.id)
                        if data_prepared and data_prepared.ks_woo_attribute_id:
                            ##Handle woo import here
                            woo_id = data_prepared.ks_woo_attribute_id
                            json_data = self.env['ks.woo.product.attribute'].ks_woo_get_attribute(woo_id, instance)
                            if json_data:
                                category = self.env['ks.woo.product.attribute'].ks_manage_attribute_import(instance,
                                                                                                           json_data)
                            else:
                                _logger.info("Fatal Error in Syncing Attributes and its values from woocommerce")

                        else:
                            _logger.info("Layer record must have woo id")
            else:
                for instance in instance_ids:
                    if push:
                        for rec in record:
                            data_prepared = rec.ks_connected_woo_attributes.filtered(
                                lambda x: x.ks_wc_instance.id == instance.id)
                            if data_prepared:
                                self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instance,
                                                                                                'ks.woo.product.attribute',
                                                                                                'product.attribute',
                                                                                                rec.id,
                                                                                                'update', True, True)
                            else:
                                self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instance,
                                                                                                'ks.woo.product.attribute',
                                                                                                'product.attribute',
                                                                                                rec.id,
                                                                                                'create', True, True)
                    elif pull:
                        for rec in record:
                            data_prepared = rec.ks_connected_woo_attributes.filtered(
                                lambda x: x.ks_wc_instance.id == instance.id)
                            woo_id = data_prepared.ks_woo_attribute_id
                            json_data = self.env['ks.woo.product.attribute'].ks_woo_get_attribute(woo_id, instance)
                            if json_data:
                                self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(
                                    instance=instance,
                                    data=[json_data])


        except Exception as e:
            _logger.info(str(e))

    def open_mapper(self):
        """
        Open mapping wizard
        :return: mapped
        """
        active_records = self._context.get("active_ids", False)
        model = self.env['ir.model'].search([('model', '=', self._name)])
        mapped = self.env['ks.global.record.mapping'].action_open_attribute_mapping_wizard(model,
                                                                                           active_records,
                                                                                           "Attribute Record Mapping")
        return mapped

    def write(self, values):
        for rec in self:
            ks_woo_prod_attr = self.env['ks.woo.product.attribute'].search([('ks_product_attribute', '=', rec.id)])
            if ks_woo_prod_attr:
                for each_ins_attr in ks_woo_prod_attr:
                    each_ins_attr.update({'ks_sync_date': datetime.datetime.now()})

        return super(KsProductAttributeInherit, self).write(values)


class KsModelProductAttribute(models.Model):
    _name = 'ks.woo.product.attribute'
    _description = "Woo Product Attribute"
    _rec_name = 'ks_name'

    # Fields need to be Connected to any Connector
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", readonly=True,
                                     help=_("WooCommerce Connector Instance reference"),
                                     ondelete='cascade')
    ks_woo_attribute_id = fields.Integer('Woo Attribute ID', readonly=True,
                                         help=_("the record id of the attribute record defined in the Connector"))
    ks_product_attribute = fields.Many2one('product.attribute', string="Odoo Product Attribute", readonly=True,
                                           ondelete='cascade', help="Displays Odoo Product Attribute Reference")
    ks_need_update = fields.Boolean(help=_("This will need to determine if a record needs to be updated, Once user "
                                           "update the record it will set as False"), readonly=True,
                                    string="Need Update")
    ks_mapped = fields.Boolean(string="Manual Mapping", readonly = True)

    # Connector Information related
    ks_name = fields.Char(string="Name", related='ks_product_attribute.name', help="Displays WooCommerce Attribute Name")
    ks_slug = fields.Char(string="Slug", help="Displays WooCommerce Attribute Slug Name")
    ks_display_type = fields.Selection([
        ('radio', 'Radio'),
        ('select', 'Select'),
        ('color', 'Color')], default='radio', string="Type", required=True,
        help="The display type used in the Product Configurator.")

    ks_sync_date = fields.Datetime('Modified On',readonly=True, help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On', readonly=True)
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

    def check_if_already_prepared(self, instance, product_attribute):
        """
        Checks if data is already prepared for exporting on layer model
        :param instance: woo instance
        :param product_attribute: woo product attribute
        :return: attribute_exist
        """
        attribute_exist = self.search([('ks_wc_instance', '=', instance.id),
                                       ('ks_product_attribute', '=', product_attribute.id)], limit=1)
        if attribute_exist:
            return attribute_exist
        else:
            return False

    def ks_action_sync_attributes_from_woo(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_woo_attribute_id and e.ks_wc_instance)
                for i in records:
                    json_data = [self.ks_woo_get_attribute(i.ks_woo_attribute_id, i.ks_wc_instance)]
                    if json_data[0]:
                        self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(data=json_data,
                                                                                          instance=i.ks_wc_instance)
                return self.env['ks.message.wizard'].ks_pop_up_message("Success",
                                                                       '''Attributes Enqueued, Please refer Logs and Queues 
                                                                       for further Details.''')
            except Exception as e:
                raise e

        else:
            try:
                self.ensure_one()
                if self.ks_woo_attribute_id:
                    data = self.ks_woo_get_attribute(self.ks_woo_attribute_id, self.ks_wc_instance)
                    attribute = self.ks_manage_attribute_import(self.ks_wc_instance, data)
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                       ks_model='product.attribute',
                                                                       ks_layer_model='ks.woo.product.attribute',
                                                                       ks_message="Attribute sync from woo successfully",
                                                                       ks_status="success",
                                                                       ks_type="attribute",
                                                                       ks_record_id=attribute.id,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=data.get("id", 0) if data else 0,
                                                                       ks_woo_instance=self.ks_wc_instance)

                    return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                           "Action Performed. Please refer logs for further details.")

            except Exception as e:
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                   ks_model='product.attribute',
                                                                   ks_layer_model='ks.woo.product.attribute',
                                                                   ks_message=str(e),
                                                                   ks_status="failed",
                                                                   ks_type="attribute",
                                                                   ks_record_id=0,
                                                                   ks_operation_flow="woo_to_odoo",
                                                                   ks_woo_id=0,
                                                                   ks_woo_instance=self.ks_wc_instance)

    def ks_action_sync_attributes_to_woo(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance)
                if len(records) > 0:
                    self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(records=records)
                    return self.env['ks.message.wizard'].ks_pop_up_message("Success",
                                                                           '''Attributes Enqueued, Please refer Logs and Queues for 
                                                                           further Details.''')
            except Exception as e:
                raise e

        else:
            self.ensure_one()
            try:
                woo_attrib_response = self.ks_manage_attribute_export()
                return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                       "Action Performed. Please refer logs for further details.")
            except Exception as e:
                raise e

    def action_woo_layer_attribute_terms(self):
        """
        opens layer model attributes values
        :return: action
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("ks_woocommerce.action_ks_woo_product_attribute_value")
        action['domain'] = [('ks_attribute_id', '=', self.ks_product_attribute.id)]
        return action

    def ks_map_attribute_data_for_odoo(self, json_data):
        data = {}
        if json_data:
            data = {
                "name": json_data.get('name'),
                "display_type": 'select',
            }
        return data

    def ks_map_attribute_data_for_layer(self, attribute_data, product_attribute, instance):
        data = {
            "ks_product_attribute": product_attribute.id,
            "ks_slug": attribute_data.get("slug"),
            "ks_wc_instance": instance.id,
            "ks_display_type": "select",
            "ks_woo_attribute_id": attribute_data.get("id")
        }
        return data

    def ks_manage_attribute_import(self, woo_instance, attribute_data, queue_record=False):
        """
        :param woo_instance:
        :param attribute_data: attributes json data
        :param queue_record: boolean trigger for queue
        :return: None
        """
        try:
            layer_attribute = self
            layer_attribute = self.search([('ks_wc_instance', '=', woo_instance.id),
                                           ("ks_woo_attribute_id", '=', attribute_data.get("id") if attribute_data else None)])
            odoo_attribute = layer_attribute.ks_product_attribute
            odoo_main_data = self.ks_map_attribute_data_for_odoo(attribute_data)
            if layer_attribute:
                try:
                    odoo_attribute.ks_manage_attribute_in_odoo(odoo_main_data.get('name'),
                                                               odoo_main_data.get('display_type'),
                                                               odoo_attribute=odoo_attribute)
                    layer_data = self.ks_map_attribute_data_for_layer(attribute_data, odoo_attribute, woo_instance)
                    layer_attribute.write(layer_data)
                    attribute_terms = self.env['ks.woo.pro.attr.value'].ks_woo_get_all_attribute_terms(woo_instance,
                                                                                                       layer_attribute.ks_woo_attribute_id)
                    if attribute_terms:
                        self.env['ks.woo.pro.attr.value'].ks_manage_attribute_value_import(woo_instance,
                                                                                           attribute_data.get("id"),
                                                                                           odoo_attribute,
                                                                                           attribute_terms,
                                                                                           queue_record=queue_record)
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                       ks_model='product.attribute',
                                                                       ks_layer_model='ks.woo.product.attribute',
                                                                       ks_message="Attribute import update success",
                                                                       ks_status="success",
                                                                       ks_type="attribute",
                                                                       ks_record_id=layer_attribute.id,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=attribute_data.get("id", 0),
                                                                       ks_woo_instance=woo_instance)
                    layer_attribute.ks_sync_date = datetime.datetime.now()
                    layer_attribute.ks_last_exported_date = layer_attribute.ks_sync_date
                    layer_attribute.sync_update()
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                       ks_model='product.attribute',
                                                                       ks_layer_model='ks.woo.product.attribute',
                                                                       ks_message=str(e),
                                                                       ks_status="failed",
                                                                       ks_type="attribute",
                                                                       ks_record_id=layer_attribute.id,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=attribute_data.get("id", 0),
                                                                       ks_woo_instance=woo_instance)
            else:
                try:
                    if attribute_data.get('id'):
                        odoo_attribute = odoo_attribute.ks_manage_attribute_in_odoo(odoo_main_data.get('name'),
                                                                                    odoo_main_data.get('display_type'),
                                                                                    odoo_attribute=odoo_attribute)
                        layer_data = self.ks_map_attribute_data_for_layer(attribute_data, odoo_attribute, woo_instance)
                        layer_attribute = self.create(layer_data)
                        attribute_terms = self.env['ks.woo.pro.attr.value'].ks_woo_get_all_attribute_terms(woo_instance,
                                                                                                           layer_attribute.ks_woo_attribute_id)
                        if attribute_terms:
                            self.env['ks.woo.pro.attr.value'].ks_manage_attribute_value_import(woo_instance,
                                                                                               attribute_data.get("id"),
                                                                                               odoo_attribute,
                                                                                               attribute_terms,
                                                                                               queue_record=queue_record)
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                           ks_model='product.attribute',
                                                                           ks_layer_model='ks.woo.product.attribute',
                                                                           ks_message="Attribute import create success",
                                                                           ks_status="success",
                                                                           ks_type="attribute",
                                                                           ks_record_id=layer_attribute.id,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=attribute_data.get("id", 0),
                                                                           ks_woo_instance=woo_instance)
                    else:
                        odoo_attribute = odoo_attribute.ks_manage_attribute_in_odoo(odoo_main_data.get('name'),
                                                                                    odoo_main_data.get(
                                                                                        'display_type'),
                                                                                    odoo_attribute=odoo_attribute)
                        for rec in attribute_data.get('options'):
                            data = {
                                "name": rec,
                                "display_type": 'select',
                                "attribute_id": odoo_attribute.id,
                            }
                            self.env['product.attribute.value'].ks_manage_attribute_value_in_odoo(data.get('name'),
                                                              odoo_attribute.id,
                                                              odoo_attribute_value=False)
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                           ks_model='product.attribute',
                                                                           ks_layer_model='ks.woo.product.attribute',
                                                                           ks_message="Attribute import create success",
                                                                           ks_status="success",
                                                                           ks_type="attribute",
                                                                           ks_record_id=layer_attribute.id,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=attribute_data.get("id", 0),
                                                                           ks_woo_instance=woo_instance)
                    layer_attribute.ks_sync_date = datetime.datetime.now()
                    layer_attribute.ks_last_exported_date = layer_attribute.ks_sync_date
                    layer_attribute.sync_update()
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                       ks_model='product.attribute',
                                                                       ks_layer_model='ks.woo.product.attribute',
                                                                       ks_message=str(e),
                                                                       ks_status="failed",
                                                                       ks_type="attribute",
                                                                       ks_record_id=0,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=attribute_data.get("id", 0),
                                                                       ks_woo_instance=woo_instance)

            return odoo_attribute
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            raise e

    def ks_prepare_export_json_data(self, odoo_attribute, layer_attribute):
        """
        prepares to export data to woo
        :return: data
        """
        data = {
            "name": odoo_attribute.name,
            "slug": layer_attribute.ks_slug if layer_attribute.ks_slug else '',
            "type": 'select'
        }
        return data

    def ks_manage_attribute_export(self, queue_record=False):
        """
        :param queue_record: Queue Boolean Trigger
        :return: json response
        """
        woo_attribute_data_response = None
        odoo_base_attribute = self.ks_product_attribute
        try:
            woo_attribute_id = self.ks_woo_attribute_id
            woo_attribute_data = self.ks_prepare_export_json_data(odoo_base_attribute, self)
            if woo_attribute_id:
                try:
                    woo_attribute_data_response = self.ks_woo_update_attribute(woo_attribute_id, woo_attribute_data,
                                                                               self.ks_wc_instance)
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_woo",
                                                                       ks_model='product.attribute',
                                                                       ks_layer_model='ks.woo.product.attribute',
                                                                       ks_message="Attribute Export Update Successful",
                                                                       ks_status="success",
                                                                       ks_type="attribute",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="odoo_to_woo",
                                                                       ks_woo_id=woo_attribute_data_response.get("id",
                                                                                                                 0) if woo_attribute_data_response else 0,
                                                                       ks_woo_instance=self.ks_wc_instance)
                    self.ks_sync_date = datetime.datetime.now()
                    self.ks_last_exported_date = self.ks_sync_date
                    self.sync_update()
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                       ks_model='product.attribute',
                                                                       ks_layer_model='ks.woo.product.attribute',
                                                                       ks_message=str(e),
                                                                       ks_status="failed",
                                                                       ks_type="attribute",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="odoo_to_woo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=self.ks_wc_instance)
            else:
                try:
                    woo_attribute_data_response = self.ks_woo_post_attribute(woo_attribute_data,
                                                                             self.ks_wc_instance)
                    if woo_attribute_data_response:
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_woo",
                                                                           ks_model='product.attribute',
                                                                           ks_layer_model='ks.woo.product.attribute',
                                                                           ks_message="Attribute Export create Successful",
                                                                           ks_status="success",
                                                                           ks_type="attribute",
                                                                           ks_record_id=self.id,
                                                                           ks_operation_flow="odoo_to_woo",
                                                                           ks_woo_id=woo_attribute_data_response.get("id",
                                                                                                                     0) if woo_attribute_data_response else 0,
                                                                           ks_woo_instance=self.ks_wc_instance)
                        self.ks_sync_date = datetime.datetime.now()
                        self.ks_last_exported_date = self.ks_sync_date
                        self.sync_update()
                    else:
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                           ks_model='product.attribute',
                                                                           ks_layer_model='ks.woo.product.attribute',
                                                                           ks_message="Attribute Export create Failed",
                                                                           ks_status="failed",
                                                                           ks_type="attribute",
                                                                           ks_record_id=self.id,
                                                                           ks_operation_flow="odoo_to_woo",
                                                                           ks_woo_id=woo_attribute_data_response.get(
                                                                               "id",
                                                                               0) if woo_attribute_data_response else 0,
                                                                           ks_woo_instance=self.ks_wc_instance)

                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                       ks_model='product.attribute',
                                                                       ks_layer_model='ks.woo.product.attribute',
                                                                       ks_message=str(e),
                                                                       ks_status="failed",
                                                                       ks_type="attribute",
                                                                       ks_record_id=self.id,
                                                                       ks_operation_flow="odoo_to_woo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=self.ks_wc_instance)
            if woo_attribute_data_response:
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(woo_attribute_data_response,
                                                                                 self,
                                                                                 'ks_woo_attribute_id',
                                                                                 {
                                                                                     "ks_slug": woo_attribute_data_response.get(
                                                                                         'slug') or ''}
                                                                                 )
            all_attribute_values = self.env['ks.woo.pro.attr.value'].search(
                [('ks_attribute_id', '=', self.ks_product_attribute.id),
                 ('ks_wc_instance', '=', self.ks_wc_instance.id)])
            all_attribute_values.ks_manage_attribute_value_export(self.ks_woo_attribute_id, queue_record)

            return woo_attribute_data_response
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            raise e

    def ks_map_prepare_data_for_layer(self, instance, product_attribute):
        """
        :param product_category: product.category()
        :param instance: ks.woo.connector.instance()
        :return: layer compatible data
        """
        data = {
            "ks_product_attribute": product_attribute.id,
            "ks_wc_instance": instance.id,
        }
        return data

    def create_woo_record(self, instance, odoo_attribute, export_to_woo=False, queue_record=False):
        """
        """
        try:
            woo_layer_exist = self.search([("ks_product_attribute", '=', odoo_attribute.id),
                                           ('ks_wc_instance', '=', instance.id)], limit=1)
            if not woo_layer_exist:
                data = self.ks_map_prepare_data_for_layer(instance, odoo_attribute)
                layer_attribute = self.create(data)
                self.env['ks.woo.pro.attr.value'].ks_manage_value_preparation(instance, odoo_attribute.value_ids)
                self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                       status="success",
                                                                       type="attribute",
                                                                       instance=instance,
                                                                       odoo_model="product.attribute",
                                                                       layer_model="ks.woo.product.attribute",
                                                                       id=odoo_attribute.id,
                                                                       message="Layer preparation Success")
                if export_to_woo:
                    try:
                        layer_attribute.ks_manage_attribute_export()
                    except Exception as e:
                        _logger.info(str(e))
                return layer_attribute
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                   status="failed",
                                                                   type="attribute",
                                                                   instance=instance,
                                                                   odoo_model="product.attribute",
                                                                   layer_model="ks.woo.product.attribute",
                                                                   id=odoo_attribute.id,
                                                                   message=str(e))

    def update_woo_record(self, instance, odoo_attribute, export_to_woo=False, queue_record=False):
        """
        """
        try:
            woo_layer_exist = self.search([("ks_product_attribute", '=', odoo_attribute.id),
                                           ('ks_wc_instance', '=', instance.id)], limit=1)
            if woo_layer_exist:
                data = self.ks_map_prepare_data_for_layer(instance, odoo_attribute)
                woo_layer_exist.write(data)
                self.env['ks.woo.pro.attr.value'].ks_manage_value_preparation(instance, odoo_attribute.value_ids)
                self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                       status="success",
                                                                       type="attribute",
                                                                       instance=instance,
                                                                       odoo_model="product.attribute",
                                                                       layer_model="ks.woo.product.attribute",
                                                                       id=odoo_attribute.id if odoo_attribute else 0,
                                                                       message="Layer preparation Success")
                if export_to_woo:
                    try:
                        woo_layer_exist.ks_manage_attribute_export()
                    except Exception as e:
                        _logger.info(str(e))
                return woo_layer_exist
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                   status="failed",
                                                                   type="attribute",
                                                                   instance=instance,
                                                                   odoo_model="product.attribute",
                                                                   layer_model="ks.woo.product.attribute",
                                                                   id=odoo_attribute.id,
                                                                   message=str(e))

    def ks_woo_get_all_attributes(self, instance_id):
        """
        Get all the attributes from api
        :param instance_id:
        :return: json data response
        """
        wc_api = instance_id.ks_woo_api_authentication()
        try:
            woo_attribute_response = wc_api.get("products/attributes")
            if woo_attribute_response.status_code in [200, 201]:
                all_retrieved_data = woo_attribute_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="attribute",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.attribute",
                                                                   message="Fetch of attribute successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="attribute",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.attribute",
                                                                   message=str(woo_attribute_response.text))
            return all_retrieved_data
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="attribute",
                                                               instance=instance_id,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.attribute",
                                                               message=str(e))

    def ks_woo_get_attribute(self, attribute_id, instance_id):
        """
        get specific attribute from api
        :param attribute_id: id of attribute
        :param instance_id: woo instance
        :return: json response
        """
        try:
            wc_api = instance_id.ks_woo_api_authentication()
            woo_attribute_response = wc_api.get("products/attributes/%s" % (attribute_id))
            if woo_attribute_response.status_code in [200, 201]:
                attribute_data = woo_attribute_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="attribute",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance_id,
                                                                   woo_id=woo_attribute_response.json().get("id"),
                                                                   layer_model="ks.woo.product.attribute",
                                                                   message="Fetch of attribute successful")
                return attribute_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="attribute",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.attribute",
                                                                   message=str(woo_attribute_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="attribute",
                                                               instance=instance_id,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.attribute",
                                                               message=str(e))

    def ks_woo_post_attribute(self, data, instance_id):
        """
        Create attribute on woo through api
        :param data: data for attribute
        :param instance_id: woo instance()
        :return: json response
        """
        try:
            wc_api = instance_id.ks_woo_api_authentication()
            woo_attribute_response = wc_api.post("products/attributes", data)
            if woo_attribute_response.status_code in [200, 201]:
                attribute_data = woo_attribute_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="attribute",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance_id,
                                                                   woo_id=attribute_data.get("id") if attribute_data else 0,
                                                                   layer_model="ks.woo.product.attribute",
                                                                   message="Create of attribute successful")
                return attribute_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="attribute",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.attribute",
                                                                   message=str(woo_attribute_response.text)) if woo_attribute_response else ''
                return False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="attribute",
                                                               instance=instance_id,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.attribute",
                                                               message=str(e))
            return False

    def ks_woo_update_attribute(self, attribute_id, data, instance_id):
        """
        :param attribute_id: woo attribute id
        :param data: woo compatible data
        :param instance_id: ks.woo.connector.instance()
        :return: woo json response
        """
        try:
            wc_api = instance_id.ks_woo_api_authentication()
            woo_attribute_response = wc_api.put("products/attributes/%s" % (attribute_id),
                                                data)
            if woo_attribute_response.status_code in [200, 201]:
                attribute_data = woo_attribute_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_woo",
                                                                   status="success",
                                                                   type="attribute",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance_id,
                                                                   woo_id=attribute_data.get("id"),
                                                                   layer_model="ks.woo.product.attribute",
                                                                   message="Update of attribute successful")
                return attribute_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="attribute",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.attribute",
                                                                   message=str(woo_attribute_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="attribute",
                                                               instance=instance_id,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.attribute",
                                                               message=str(e))
