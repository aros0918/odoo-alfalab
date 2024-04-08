# -*- coding: utf-8 -*-

from odoo import api, fields, models


class KsWooLogs(models.Model):
    _name = "ks.woo.logger"
    _rec_name = "ks_log_id"
    _order = 'create_date desc'
    _description = "Used to maintain logging of all kind of woo operations"

    ks_name = fields.Char("Name", default="Not Available")
    ks_log_id = fields.Char(string="Log Id", readonly=True, default=lambda self: 'New')
    ks_operation_performed = fields.Selection([('create_post', 'Create in Post'), ('create_woo', 'Create in Woo'),
                                               ('create_odoo', 'Create in Odoo'),
                                               ('create', 'Create'), ('update', 'Update'),
                                               ('prepare_create', 'Prepare Create'),
                                               ('prepare_update', 'Prepare Update'),
                                               ('cancel', 'Cancel'), ('update_post', 'Update in Post'),
                                               ('update_woo', 'Update in Woo'), ('update_odoo', 'Update in Odoo'),
                                               ('fetch', 'Fetch'), ('import', 'Import'),
                                               ('map_product','Mapping Products'),
                                               ('map_customer','Mapping Customer'),
                                               ('export', 'Export'), ('refund', 'Refund'), ('conn', 'Connection')],
                                              string="Operation Performed", help="Displays operation type which is performed")
    ks_type = fields.Selection([('order', 'Orders'), ('product', 'Product'), ('product_variant', 'Product Variant'),
                                ('stock', 'Stock'), ('price', 'Price'), ('category', 'Category'), ('tags', 'Tags'),
                                ('customer', 'Customer'), ('payment_gateway', 'Payment Gateway'), ('coupon', 'Coupon'),
                                ('attribute', 'Attribute'), ('attribute_value', 'Attribute Values'), ('tax', 'Tax'),
                                ('system_status', 'System Status'), ('webhook', "Webhook"),('shipping','Shipping Methods')],
                               string="Domain", help="Shows name of the model")
    ks_woo_instance = fields.Many2one("ks.woo.connector.instance", string="WooCommerce Instance", help="Displays WooCommerce Instance Name")
    ks_record_id = fields.Integer(string="Odoo Record ID", help="Displays the odoo record ID")
    ks_message = fields.Text(string="Logs Message", help="Displays the Summary of the Logs")
    ks_model = fields.Many2one("ir.model", string="Odoo Model Associated", help="Displays the odoo default model which is associated")
    ks_layer_model = fields.Many2one("ir.model", string="Layer Model Associated", help="Displays the layer model which is associated")
    ks_woo_id = fields.Integer(string="Woocommerce ID")
    ks_operation_flow = fields.Selection([('odoo_to_wl', "Odoo to WooCommerce Layer"),
                                          ('odoo_to_woo', "Odoo to WooCommerce"),
                                          ('wl_to_odoo', "WooCommerce Layer to Odoo"),
                                          ('woo_to_wl', "WooCommerce to WooCommerce Layer"),
                                          ('wl_to_woo', "WooCommerce Layer to WooCommerce"),
                                          ('woo_to_odoo', "WooCommerce to Odoo")],
                                         string="Operation Flow", help="Shows the flow of the operation either from WooCommerce to Odoo or Odoo to WooCommerce")
    ks_status = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Operation Status", help="Displays the status of the operation Success/Failed")
    ks_prepare = fields.Boolean(string="Prepare Operation")
    ks_api = fields.Boolean(string="API Operation")
    ks_product_id = fields.Many2one('product.template', string="Product")
    ks_product_variant_id = fields.Many2one('product.product', string="Product Variant")
    ks_product_attribute_id = fields.Many2one('product.attribute', string="Product Attribute")
    ks_product_category_id = fields.Many2one('product.category', string="Product Category")
    ks_product_tags_id = fields.Many2one('ks.woo.product.tag', string="Product Tags")
    ks_payment_gateways_id = fields.Many2one('ks.woo.payment.gateway', string="Payment Gateway")
    ks_sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    ks_coupon_id = fields.Many2one('ks.woo.coupons', string="Coupon")
    ks_product_attribute_value_id = fields.Many2one('product.attribute.value', string="Product Attribute Value")
    ks_contact_id = fields.Many2one('res.partner', string="Customer")
    ks_company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,
                                    required=True, readonly=True, help=" Shows the name of the company")

    @api.model_create_multi
    def create(self, vals_list):
        """
        Creates log records with auto unique sequence
        :param vals: creation data
        :return: super
        """
        for vals in vals_list:
            seq = self.env['ir.sequence'].next_by_code('increment_your_field') or ('New')
            vals['ks_log_id'] = seq
        return super(KsWooLogs, self).create(vals)

    def ks_create_prepare_log_params(self, operation_performed, status, instance, id, message, odoo_model=False,
                                     layer_model=False, type=False):
        """
        :param operation_performed: type of operation performed
        :param status: status of operation (failed/success)
        :param type: Domain on which operation performed
        :param instance: ks.woo.connector.instance()
        :param odoo_model: ir.model()
        :param layer_model: ir.model()
        :param id:
        :param message:
        :return:
        """
        ks_model = ks_layer_model = False
        if odoo_model:
            ks_model = self.env['ir.model']._get(odoo_model).id
        if layer_model:
            ks_layer_model = self.env['ir.model']._get(layer_model).id
        params = {
            "ks_operation_performed": operation_performed,
            "ks_status": status,
            "ks_type": type,
            "ks_operation_flow": "odoo_to_woo",
            "ks_woo_instance": instance.id if instance else False,
            "ks_model": ks_model,
            "ks_layer_model": ks_layer_model,
            "ks_record_id": id,
            "ks_message": message
        }
        params = self.ks_assign_record_with_record(type, id or 0, params)
        self.create(params)

    def ks_assign_record_with_record(self, type, id, params):
        """
        Assigning the default model id to the fields
        :param type: Data type
        :param id: ID of the record
        :param params: parameters of the logs
        :return: None
        """
        if type == 'order' and id:
            ks_sale_order = self.ks_sale_order_id.browse(id)
            if ks_sale_order:
                params.update({
                    'ks_sale_order_id': ks_sale_order.id,
                    'ks_name': ks_sale_order.name
                })
        if type == 'product' and id:
            ks_product_template = self.env['ks.woo.product.template'].browse(id)
            if ks_product_template:
                params.update({
                    'ks_product_id': self.ks_product_id.search([('id', '=', ks_product_template.id)], limit=1).id,
                    'ks_name': self.ks_product_id.search([('id', '=', ks_product_template.id)], limit=1).name
                })
        if type == 'product_variant' and id:
            params.update({
                'ks_product_variant_id': self.ks_product_variant_id.search([('id', '=', self.env['ks.woo.product.variant'].browse(id).ks_product_variant.id)], limit=1).id,
                'ks_name': self.ks_product_variant_id.search([('id', '=', self.env['ks.woo.product.variant'].browse(id).ks_product_variant.id)], limit=1).name
            })
        if type == 'category' and id:
            params.update({
                'ks_product_category_id': self.ks_product_category_id.search([('id', '=', self.env['ks.woo.product.category'].browse(id).ks_product_category.id)], limit=1).id,
                'ks_record_id': self.ks_product_category_id.search([('id', '=', self.env['ks.woo.product.category'].browse(id).ks_product_category.id)], limit=1).id,
                'ks_name': self.ks_product_category_id.search([('id', '=', self.env['ks.woo.product.category'].browse(id).ks_product_category.id)], limit=1).name,
            })
        if type == 'tags' and id:
            params.update({
                'ks_product_tags_id': self.ks_product_tags_id.search([('id', '=', id)], limit=1).id,
                'ks_name': self.ks_product_tags_id.search([('id', '=', id)], limit=1).ks_name,
            })
        if type == 'payment_gateway' and id:
            params.update({
                'ks_payment_gateways_id': self.ks_payment_gateways_id.search([('id', '=', id)], limit=1).id,
                'ks_name': self.ks_payment_gateways_id.search([('id', '=', id)], limit=1).ks_title,
            })
        if type == 'coupon' and id:
            params.update({
                'ks_coupon_id': self.ks_coupon_id.search([('id', '=', id)], limit=1).id,
                'ks_name': self.ks_coupon_id.search([('id', '=', id)], limit=1).ks_coupon_code,
            })
        if type == 'attribute' and id:
            params.update({
                'ks_product_attribute_id': self.ks_product_attribute_id.search([('id', '=', id)], limit=1).id,
                'ks_name': self.ks_product_attribute_id.search([('id', '=', id)], limit=1).name,
            })
        if type == 'attribute_value' and id:
            params.update({
                'ks_product_attribute_value_id': self.ks_product_attribute_value_id.search([('id', '=', self.env['ks.woo.pro.attr.value'].browse(id).ks_pro_attr_value.id)], limit=1).id,
                'ks_name': self.ks_product_attribute_value_id.search([('id', '=', self.env['ks.woo.pro.attr.value'].browse(id).ks_pro_attr_value.id)], limit=1).name,
            })
        if type == 'customer' and id:
            params.update({
                'ks_contact_id': self.ks_contact_id.browse(id).id,
                'ks_name': self.ks_contact_id.browse(id).name,
            })
        return params

    def ks_assign_record_with_woo_id(self, type, ks_woo_instance, id, params):
        """
        Assigning the Woo ID to the default model in the log
        :param ks_woo_instance: Woo Instance
        :param type: Data type
        :param id: ID of the record
        :param params: parameters of the logs
        :return: None
        """
        if type == 'order' and id:
            ks_sale_order = self.ks_sale_order_id.search(
                [('ks_woo_order_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)], limit=1)
            if ks_sale_order:
                params.update({
                    'ks_sale_order_id': ks_sale_order.id,
                    'ks_name': ks_sale_order.name,
                })
        if type == 'product' and id:
            ks_product_template = self.env['ks.woo.product.template'].search(
                [('ks_woo_product_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)])
            if ks_product_template:
                params.update({
                    'ks_product_id': self.ks_product_id.search(
                        [('id', '=', ks_product_template.ks_product_template.id)], limit=1).id,
                    'ks_name': self.ks_product_id.search(
                        [('id', '=', ks_product_template.ks_product_template.id)], limit=1).name,
                })
        if type == 'product_variant' and id:
            ks_product_variant = self.env['ks.woo.product.variant'].search(
                [('ks_woo_variant_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)])
            if ks_product_variant:
                params.update({
                    'ks_product_variant_id': self.ks_product_variant_id.search(
                        [('id', '=', ks_product_variant.ks_product_variant.id)], limit=1).id,
                    'ks_name': self.ks_product_variant_id.search(
                        [('id', '=', ks_product_variant.ks_product_variant.id)], limit=1).name,
                })
        if type == 'category' and id:
            ks_category = self.env['ks.woo.product.category'].search(
                [('ks_woo_category_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)])
            if ks_category:
                params.update({
                    'ks_product_category_id': self.ks_product_category_id.search(
                        [('id', '=', ks_category.ks_product_category.id)], limit=1).id,
                    'ks_name': self.ks_product_category_id.search(
                        [('id', '=', ks_category.ks_product_category.id)], limit=1).name,
                })
        if type == 'tags' and id:
            params.update({
                'ks_product_tags_id': self.ks_product_tags_id.search(
                    [('ks_woo_tag_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)], limit=1).id,
                'ks_name': self.ks_product_tags_id.search(
                    [('ks_woo_tag_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)], limit=1).ks_name,
            })
        if type == 'payment_gateway' and id:
            params.update({
                'ks_payment_gateways_id': self.ks_payment_gateways_id.search(
                    [('ks_woo_pg_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)], limit=1).id,
                'ks_name': self.ks_payment_gateways_id.search(
                    [('ks_woo_pg_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)], limit=1).ks_title,
            })
        if type == 'coupon' and id:
            params.update({
                'ks_coupon_id': self.ks_coupon_id.search(
                    [('ks_woo_coupon_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)], limit=1).id,
                'ks_name': self.ks_coupon_id.search(
                    [('ks_woo_coupon_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)], limit=1).ks_coupon_code,
            })
        if type == 'attribute' and id:
            ks_attribute = self.env['ks.woo.product.attribute'].search(
                [('ks_woo_attribute_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)])
            if ks_attribute:
                params.update({
                    'ks_product_attribute_id': self.ks_product_attribute_id.search(
                        [('id', '=', ks_attribute.ks_product_attribute.id)], limit=1).id,
                    'ks_name': self.ks_product_attribute_id.search(
                        [('id', '=', ks_attribute.ks_product_attribute.id)], limit=1).name,
                })
        if type == 'attribute_value' and id:
            ks_attribute_value = self.env['ks.woo.pro.attr.value'].search(
                [('ks_woo_attribute_term_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)])
            if ks_attribute_value:
                params.update({
                    'ks_product_attribute_value_id': self.ks_product_attribute_value_id.search(
                        [('id', '=', ks_attribute_value.ks_pro_attr_value.id)], limit=1).id,
                    'ks_name': self.ks_product_attribute_value_id.search(
                        [('id', '=', ks_attribute_value.ks_pro_attr_value.id)], limit=1).name,
                })
        if type == 'customer' and id:
            ks_contact = self.env['ks.woo.partner'].search(
                [('ks_woo_partner_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)])
            if ks_contact:
                params.update({
                    'ks_contact_id': self.ks_contact_id.search([('id', '=', ks_contact.ks_res_partner.id)], limit=1).id,
                    'ks_name': self.ks_contact_id.search([('id', '=', ks_contact.ks_res_partner.id)], limit=1).name,
                })
        return params

    def ks_create_api_log_params(self, operation_performed, status, operation_flow, type, instance, woo_id, message,
                                 layer_model=False, ks_record_id=False):
        """
        :param operation_performed: type of operation performed
        :param status: status of operation (failed/success)
        :param operation_flow: flow (woo_to_odoo/odoo_to_woo)
        :param type: Domain on which operation performed
        :param instance: ks.woo.connector.instance()
        :param woo_id: woocommerce id
        :param layer_model:
        :return:
        """
        ks_layer_model = False
        if layer_model:
            ks_layer_model = self.env['ir.model']._get(layer_model).id

        params = {
            "ks_operation_performed": operation_performed,
            "ks_status": status,
            "ks_operation_flow": operation_flow,
            "ks_type": type,
            "ks_woo_instance": instance.id if instance else False,
            "ks_woo_id": woo_id or 0,
            "ks_layer_model": ks_layer_model,
            "ks_message": message,
            "ks_record_id": ks_record_id
        }
        params = self.ks_assign_record_with_woo_id(type, instance, woo_id or 0, params)
        self.create(params)

    def ks_create_odoo_log_param(self, ks_operation_performed, ks_status, ks_operation_flow, ks_type, ks_woo_instance,
                                 ks_woo_id, ks_record_id, ks_message, ks_model=False, ks_layer_model=False):
        """
        Generic method to create logs
        :param ks_operation_performed: type of operation
        :param ks_type: domain name
        :param ks_woo_instance: woocommerce instance
        :param ks_record_id: odoo record id
        :param ks_message: process conclusion message
        :param ks_woo_id: woo unique id
        :param ks_operation_flow: operation flow
        :param ks_status: operation status
        :param ks_model: model id
        :param ks_layer_model: layer model id
        :param ks_error: error
        :return:
        """
        if ks_model:
            ks_model = self.env['ir.model']._get(ks_model).id
        if ks_layer_model:
            ks_layer_model = self.env['ir.model']._get(ks_layer_model).id
        params = {
            'ks_operation_performed': ks_operation_performed,
            'ks_type': ks_type,
            'ks_woo_instance': ks_woo_instance.id if ks_woo_instance else False,
            'ks_record_id': ks_record_id,
            'ks_message': ks_message,
            'ks_model': ks_model,
            'ks_woo_id': ks_woo_id if ks_woo_id else 0,
            'ks_layer_model': ks_layer_model,
            'ks_operation_flow': ks_operation_flow,
            'ks_status': ks_status
        }
        params = self.ks_assign_record_with_woo_id(ks_type, ks_woo_instance, ks_woo_id or 0, params)
        self.create(params)

    def ks_create_log_param(self, ks_operation_performed, ks_type, ks_woo_instance, ks_record_id, ks_message,
                            ks_woo_id, ks_operation_flow, ks_status, ks_model=False, ks_layer_model=False,
                            ks_error=False):
        """
        Generic method to create logs
        :param ks_operation_performed: type of operation
        :param ks_type: domain name
        :param ks_woo_instance: woocommerce instance
        :param ks_record_id: odoo record id
        :param ks_message: process conclusion message
        :param ks_woo_id: woo unique id
        :param ks_operation_flow: operation flow
        :param ks_status: operation status
        :param ks_model: model id
        :param ks_layer_model: layer model id
        :param ks_error: error
        :return:
        """
        if ks_model:
            ks_model = self.env['ir.model']._get(ks_model).id
        if ks_layer_model:
            ks_layer_model = self.env['ir.model']._get(ks_layer_model).id
        params = {
            'ks_operation_performed': ks_operation_performed,
            'ks_type': ks_type,
            'ks_woo_instance': ks_woo_instance.id if ks_woo_instance else False,
            'ks_record_id': ks_record_id,
            'ks_message': ks_message if not (ks_error) else (ks_message + " " + str(ks_error)),
            'ks_model': ks_model,
            'ks_woo_id': ks_woo_id if ks_woo_id else 0,
            'ks_layer_model': ks_layer_model,
            'ks_operation_flow': ks_operation_flow,
            'ks_status': ks_status
        }
        params = self.ks_assign_record_with_woo_id(ks_type, ks_woo_instance, ks_woo_id or 0, params)
        self.create(params)
