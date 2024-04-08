# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class KsMapResPartnerWizard(models.TransientModel):
    _name = "map.res.partner.wizard"
    _description = "WooCommerce Partner Mapping"

    res_partner_line_ids = fields.One2many("map.wizard.line", "res_partner_wizard_id", string="Customers")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance id",
                                     domain=[('ks_instance_state', '=', 'active')])
    ks_sync_operation = fields.Selection(
        [('push_to_woo', 'Push to Woocommerce'), ('pull_from_woo', 'Pull from Woocommerce')],
        string="Sync operation", default=False)

    @api.onchange('ks_wc_instance')
    @api.depends('ks_wc_instance')
    def check_instance(self):
        self.res_partner_line_ids.update({'ks_wc_instance': self.ks_wc_instance.id})

    def map_customers_records(self):
        count_instance = 0
        for reco in self.res_partner_line_ids:
            if reco.ks_wc_instance:
                count_instance += 1
        if count_instance != len(self.res_partner_line_ids):
            raise ValidationError("Cannot Map without Instance")
        for line in self.res_partner_line_ids:
            already_exist = self.env['ks.woo.partner'].search([('ks_woo_partner_id', '=', line.ks_record_id),
                                                               ('ks_wc_instance', '=', line.ks_wc_instance.id)])
            if already_exist:
                raise ValidationError(
                    "Woo Id already within given instance already exists.in record *%s* with id given: %s" % (
                        already_exist.display_name, already_exist.ks_woo_partner_id))
            layer_record = line.ks_base_model_customer.ks_partner_ids.filtered(
                lambda x: x.ks_wc_instance.id == line.ks_wc_instance.id)
            if layer_record:
                layer_record = self.env['ks.woo.partner'].update_woo_record(line.ks_wc_instance,
                                                                            line.ks_base_model_customer)
            else:
                layer_record = self.env['ks.woo.partner'].create_woo_record(line.ks_wc_instance,
                                                                            line.ks_base_model_customer)
            if layer_record:
                layer_record.update({
                    'ks_woo_partner_id': line.ks_record_id,
                    'ks_mapped': True
                })
            if self.ks_sync_operation == 'push_to_woo':
                ##Handle export operation here
                try:
                    self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance=line.ks_wc_instance,
                                                                                     records=layer_record)
                except Exception as e:
                    _logger.info(str(e))
            elif self.ks_sync_operation == 'pull_from_woo':
                ##Handle import operation here
                try:
                    woo_id = layer_record.ks_woo_partner_id
                    json_data = self.env['ks.woo.partner'].ks_woo_get_customer(woo_id, layer_record.ks_wc_instance)
                    if json_data:
                        self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(
                            instance=layer_record.ks_wc_instance,
                            data=[json_data])
                except Exception as e:
                    _logger.info(str(e))


class KsMapProductCategory(models.TransientModel):
    _name = "map.product.category.wizard"
    _description = "WooCommerce Product Category Mapping"

    category_line_ids = fields.One2many("map.wizard.line", "product_category_tag_wizard_id", string="Category")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance id",
                                     domain=[('ks_instance_state', '=', 'active')])
    ks_sync_operation = fields.Selection(
        [('push_to_woo', 'Push to Woocommerce'), ('pull_from_woo', 'Pull from Woocommerce')],
        string="Sync records to woocommerce", default=False)

    @api.onchange('ks_wc_instance')
    @api.depends('ks_wc_instance')
    def check_instance(self):
        self.category_line_ids.update({'ks_wc_instance': self.ks_wc_instance.id})

    def map_category_records(self):
        count_instance = 0
        for reco in self.category_line_ids:
            if reco.ks_wc_instance:
                count_instance += 1
        if count_instance != len(self.category_line_ids):
            raise ValidationError("Cannot Map without Instance")
        for line in self.category_line_ids:
            already_exist = self.env['ks.woo.product.category'].search([('ks_woo_category_id', '=', line.ks_record_id),
                                                                        (
                                                                            'ks_wc_instance', '=',
                                                                            line.ks_wc_instance.id)])
            if already_exist:
                raise ValidationError(
                    "Woo Id already exists for the given instance in record *%s* with id given: %s" % (
                        already_exist.display_name, already_exist.ks_woo_category_id))
            layer_record = line.ks_base_model_category.ks_product_category.filtered(
                lambda x: x.ks_wc_instance.id == line.ks_wc_instance.id)
            if layer_record:
                layer_record = self.env['ks.woo.product.category'].update_woo_record(line.ks_wc_instance,
                                                                                     line.ks_base_model_category)
            else:
                layer_record = self.env['ks.woo.product.category'].create_woo_record(line.ks_wc_instance,
                                                                                     line.ks_base_model_category)

            if layer_record:
                layer_record.update({
                    'ks_woo_category_id': line.ks_record_id,
                    'ks_mapped': True
                })

            if self.ks_sync_operation == 'push_to_woo':
                ##Handle category export here
                try:
                    self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(
                        instance=layer_record.ks_wc_instance,
                        records=layer_record)
                except Exception as e:
                    _logger.info(str(e))
            elif self.ks_sync_operation == 'pull_from_woo':
                ##Handle category import here
                try:
                    woo_id = layer_record.ks_woo_category_id
                    json_data = self.env['ks.woo.product.category'].ks_woo_get_category(woo_id,
                                                                                        instance=layer_record.ks_wc_instance)
                    if json_data:
                        self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(
                            instance=layer_record.ks_wc_instance,
                            data=[json_data])
                except Exception as e:
                    _logger.info(str(e))


class KsMapProductAttributes(models.TransientModel):
    _name = "map.product.attribute.wizard"
    _description = "WooCommerce Product Attribute and its Values Mapping"

    attribute_line_ids = fields.One2many("map.wizard.line", "product_attribute_wizard_id", string="Attribute")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance id",
                                     domain=[('ks_instance_state', '=', 'active')])
    ks_sync_operation = fields.Selection(
        [('push_to_woo', 'Push to Woocommerce'), ('pull_from_woo', 'Pull from Woocommerce')],
        string="Sync records to woocommerce", default=False)

    @api.onchange('ks_wc_instance')
    @api.depends('ks_wc_instance')
    def check_instance(self):
        self.attribute_line_ids.update({'ks_wc_instance': self.ks_wc_instance.id})

    def map_attributes_records(self):
        attribute_domains = []
        attribute_ids = []
        instances = []
        count_instance = 0
        for reco in self.attribute_line_ids:
            if reco.ks_wc_instance:
                count_instance += 1
        if count_instance != len(self.attribute_line_ids):
            raise ValidationError("Cannot Map without Instance")
        for line in self.attribute_line_ids:
            if line.ks_base_model_attribute:
                layer_record = None
                already_exist = self.env["ks.woo.product.attribute"].search(
                    [('ks_wc_instance', '=', line.ks_wc_instance.id),
                     ('ks_woo_attribute_id', '=', line.ks_record_id)])
                if already_exist:
                    raise ValidationError(
                        "Woo Id already exists for the given instance in record *%s* with id given: %s" % (
                            already_exist.display_name, already_exist.ks_woo_attribute_id))
                layer_record = line.ks_base_model_attribute.ks_connected_woo_attributes.filtered(
                    lambda x: x.ks_wc_instance.id == line.ks_wc_instance.id)
                if layer_record:
                    layer_record = self.env["ks.woo.product.attribute"].update_woo_record(line.ks_wc_instance,
                                                                                          line.ks_base_model_attribute)
                else:
                    layer_record = self.env["ks.woo.product.attribute"].create_woo_record(line.ks_wc_instance,
                                                                                          line.ks_base_model_attribute)
                layer_record.update({
                    'ks_woo_attribute_id': line.ks_record_id,
                    'ks_mapped': True
                })
                if layer_record.id not in attribute_ids:
                    attribute_domains.append(layer_record)
                    instances.append(layer_record.ks_wc_instance.id)
                    attribute_ids.append(layer_record.id)
            if line.ks_base_model_attribute_value:
                already_exist = self.env["ks.woo.pro.attr.value"].search(
                    [('ks_wc_instance', '=', line.ks_wc_instance.id),
                     ('ks_woo_attribute_term_id', '=', line.ks_record_id)])
                if already_exist:
                    raise ValidationError(
                        "Woo Id already exists for the given instance in record *%s* with id given: %s" % (
                            already_exist.display_name, already_exist.ks_woo_attribute_term_id))
                parent_attribute = line.ks_base_model_attribute_value.attribute_id
                parent_instance = self.attribute_line_ids.filtered(
                    lambda x: x.ks_base_model_attribute.id == parent_attribute.id).ks_wc_instance
                if parent_instance.id != line.ks_wc_instance.id:
                    raise ValidationError("Attribute Value instance should be same as Attribute instance")
                value_record = line.ks_base_model_attribute_value.ks_connected_woo_attribute_terms.filtered(
                    lambda x: (x.ks_wc_instance.id == line.ks_wc_instance.id) and (
                            x.ks_attribute_id.id == line.ks_base_model_attribute_value.attribute_id.id) and (
                                      x.ks_pro_attr_value.id == line.ks_base_model_attribute_value.id))
                if value_record:
                    value_record = self.env["ks.woo.pro.attr.value"].update_woo_record(line.ks_wc_instance,
                                                                                       line.ks_base_model_attribute_value)
                else:
                    value_record = self.env["ks.woo.pro.attr.value"].create_woo_record(line.ks_wc_instance,
                                                                                       line.ks_base_model_attribute_value)
                if value_record:
                    value_record.update({
                        'ks_woo_attribute_term_id': str(line.ks_record_id),
                        'ks_mapped': True
                    })

            if attribute_domains:
                try:
                    for instance, attribute in enumerate(attribute_domains):
                        instance_id = self.env['ks.woo.connector.instance'].browse(instances[instance])
                        layer_record = attribute
                        if self.ks_sync_operation == 'push_to_woo':
                            self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(instance=instance_id,
                                                                                              records=layer_record)
                        if self.ks_sync_operation == 'pull_from_woo':
                            woo_id = layer_record.ks_woo_attribute_id
                            json_data = self.env['ks.woo.product.attribute'].ks_woo_get_attribute(woo_id, instance_id)
                            if json_data:
                                self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(instance=instance_id,
                                                                                                  data=[json_data])
                except Exception as e:
                    _logger.info(str(e))


class KsMapProduct(models.TransientModel):
    _name = "map.product.wizard"
    _description = "WooCommerce Product Variant Mapping"

    product_line_ids = fields.One2many("map.wizard.line", "product_wizard_id", string="Product")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance id",
                                     domain=[('ks_instance_state', '=', 'active')])
    ks_sync_operation = fields.Selection(
        [('push_to_woo', 'Push to Woocommerce'), ('pull_from_woo', 'Pull from Woocommerce')],
        string="Sync records to woocommerce", default=False)
    ks_filled = fields.Boolean(compute="_check_filled", readonly=True)

    @api.onchange('ks_wc_instance')
    @api.depends('ks_wc_instance')
    def check_instance(self):
        self.product_line_ids.update({'ks_wc_instance': self.ks_wc_instance.id})

    def map_product_records(self):
        parent = None
        product_template = []
        product_template_ids = []
        instance_ids = []
        count_instance = 0
        for reco in self.product_line_ids:
            if reco.ks_wc_instance:
                count_instance+=1
        if count_instance != len(self.product_line_ids):
            raise ValidationError("Cannot Map without Instance")
        for line in self.product_line_ids:
            if line.ks_base_model_product:
                already_exist = self.env['ks.woo.product.template'].search(
                    [('ks_wc_instance', '=', line.ks_wc_instance.id),
                     ('ks_woo_product_id', '=', line.ks_record_id)])
                if already_exist:
                    raise ValidationError(
                        "Woo Id already exists for the given instance in record *%s* for the id given: %s" % (
                            already_exist.display_name, already_exist.ks_woo_product_id))
                parent = line.ks_base_model_product
                layer_record = line.ks_base_model_product.ks_product_template.filtered(
                    lambda x: x.ks_wc_instance.id == line.ks_wc_instance.id)
                if layer_record:
                    layer_record = self.env['ks.woo.product.template'].update_woo_record(line.ks_wc_instance,
                                                                                         line.ks_base_model_product)
                else:
                    layer_record = self.env['ks.woo.product.template'].create_woo_record(line.ks_wc_instance,
                                                                                         line.ks_base_model_product)
                if layer_record:
                    layer_record.update({
                        'ks_woo_product_id': line.ks_record_id,
                        'ks_mapped': True
                    })
                if line.ks_base_model_product.id not in product_template_ids:
                    product_template.append(line.ks_base_model_product)
                    product_template_ids.append(line.ks_base_model_product.id)
                    instance_ids.append(line.ks_wc_instance.id)
            elif line.ks_base_model_product_variant:
                already_exist = self.env['ks.woo.product.variant'].search(
                    [('ks_wc_instance', '=', line.ks_wc_instance.id),
                     ('ks_woo_variant_id', '=', line.ks_record_id)])
                if already_exist:
                    raise ValidationError(
                        "Woo Id already exists for the given instance in record *%s* for the id given: %s" % (
                            already_exist.display_name, already_exist.ks_woo_variant_id))
                template = line.ks_base_model_product_variant.product_tmpl_id
                template_instance = self.product_line_ids.filtered(
                    lambda x: x.ks_base_model_product.id == template.id).ks_wc_instance
                if template_instance.id != line.ks_wc_instance.id:
                    raise ValidationError("Variant instance should be same as Template instance")
                layer_variants = parent.ks_product_template.ks_wc_variant_ids.filtered(
                    lambda x: (x.ks_wc_instance.id == line.ks_wc_instance.id) and (
                            x.ks_product_variant.id == line.ks_base_model_product_variant.id)
                )
                if layer_variants:
                    layer_variants.update({
                        'ks_woo_variant_id': line.ks_record_id,
                        'ks_mapped': True
                    })
                if template.id not in product_template_ids:
                    product_template.append(template)
                    product_template_ids.append(template.id)
                    instance_ids.append(template_instance.id)
        if product_template:
            try:
                for instance, template in enumerate(product_template):
                    layer_record = template.ks_product_template.filtered(
                        lambda x: x.ks_wc_instance.id == instance_ids[instance])
                    instance_id = self.env['ks.woo.connector.instance'].browse(instance_ids[instance])
                    if layer_record:
                        if self.ks_sync_operation == 'push_to_woo':
                            self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=instance_id,
                                                                                            records=layer_record)
                        if self.ks_sync_operation == 'pull_from_woo':
                            woo_id = layer_record.ks_woo_product_id
                            json_data = self.env["ks.woo.product.template"].ks_woo_get_product(woo_id, instance_id)
                            if json_data:
                                self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=instance_id,
                                                                                                data=[json_data])

            except Exception as e:
                _logger.info(str(e))


class KsMapWizardLine(models.TransientModel):
    _name = "map.wizard.line"
    _description = "Record Line for mapping"

    res_partner_wizard_id = fields.Many2one("map.res.partner.wizard")
    product_category_tag_wizard_id = fields.Many2one("map.product.category.wizard")
    product_attribute_wizard_id = fields.Many2one("map.product.attribute.wizard")
    product_wizard_id = fields.Many2one("map.product.wizard")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="WooCommerce Instance",
                                     domain=[('ks_instance_state', '=', 'active')])
    ks_id = fields.Integer(string="Odoo ID", readonly=True)
    ks_record_id = fields.Integer(string="Woo Mapping ID")
    name = fields.Char(string="Name", readonly=True)
    ks_base_model_customer = fields.Many2one("res.partner", string="Odoo Partner", readonly=True)
    ks_base_model_attribute = fields.Many2one("product.attribute", string="Odoo Attribute", readonly=True)
    ks_base_model_attribute_value = fields.Many2one("product.attribute.value", string="Odoo Attribute Value",
                                                    readonly=True)
    ks_base_model_category = fields.Many2one("product.category", string="Odoo Category", readonly=True)
    ks_base_model_product = fields.Many2one("product.template", string="Odoo Product Template", readonly=True)
    ks_base_model_product_variant = fields.Many2one("product.product", string="Odoo Product Variant",
                                                    readonly=True)
