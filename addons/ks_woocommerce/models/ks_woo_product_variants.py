from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import traceback

_logger = logging.getLogger(__name__)


class KsWooProductVariant(models.Model):
    _name = "ks.woo.product.variant"
    _rec_name = "ks_product_variant"
    _description = "Woo Product Variant"

    # ks_name = fields.Char('Name')
    ks_length = fields.Float(string='Length')
    ks_width = fields.Float(string='Width')
    ks_height = fields.Float(string='Height')
    ks_weight = fields.Float(string='Weight')
    ks_volume = fields.Float(string='Volume', compute="_ks_compute_volume", store=True)
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", readonly=True,
                                     help=_("WooCommerce Connector Instance reference"), ondelete='cascade')

    ks_woo_variant_id = fields.Integer(string='Record ID',
                                       help=_("the record id of the particular record defied in the Connector"))
    ks_date_created = fields.Datetime(string='Date Created',
                                      help=_("The date on which the record is created on the Connected"
                                             " Connector Instance"), readonly=True)
    ks_date_updated = fields.Datetime(string='Date Updated',
                                      help=_("The latest date on which the record is updated on the"
                                             " Connected Connector Instance"), readonly=True)
    ks_woo_rp_pricelist = fields.Many2one("product.pricelist.item", compute="_ks_calculate_prices", store=True,
                                          string="Regular Pricelist Item", help="Displays WooCommerce Regular Price")
    ks_woo_sp_pricelist = fields.Many2one("product.pricelist.item", compute="_ks_calculate_prices", store=True,
                                          string="Sale Pricelist Item", help="Displays WooCommerce Sale Price")
    ks_woo_regular_price = fields.Char(string='Woo Regular Price', related="ks_woo_rp_pricelist.price")
    ks_woo_sale_price = fields.Char(string='Woo Sale Price', related="ks_woo_sp_pricelist.price")
    ks_product_variant = fields.Many2one('product.product', string='Odoo Product Variant', readonly=True,
                                         help="Displays Odoo Linked Product Variant Name")
    ks_name = fields.Char(string="Name", related="ks_product_variant.name")
    ks_wc_product_tmpl_id = fields.Many2one('ks.woo.product.template', string="Woo Product Template", readonly=True,
                                            ondelete='cascade', help="Displays WooCommerce Product Template Name")
    ks_wc_image_ids = fields.One2many('ks.woo.product.images', 'ks_wc_variant_id', string='Images', readonly=True)
    # ks_wc_manage_stock = fields.Boolean("Manage Stock in Woo")
    ks_woo_description = fields.Html(string="Description",
                                     help="Message displayed as product description on WooCommerce")
    ks_default_code = fields.Char(string='Default Code')
    # ks_manage_template = fields.Char('Manage Template', default=False)
    # ks_sync_states = fields.Boolean(string="Sync Status", compute='compute_sync_status', readonly=True)
    ks_active = fields.Boolean(string="Variant Active", default=False, help="Enables/Disables the variant")
    ks_mapped = fields.Boolean(string="Manual Mapping", readonly=True)
    ks_company_id = fields.Many2one('res.company', string="Company",
                                    default=lambda self: self.ks_wc_instance.ks_company_id.id,
                                    required=True, readonly=True, help=" Shows the name of the company")

    @api.depends('ks_wc_instance', 'ks_wc_instance.ks_woo_regular_pricelist', 'ks_wc_instance.ks_woo_sale_pricelist',
                 'ks_product_variant')
    def _ks_calculate_prices(self):
        for rec in self:
            rec.ks_woo_rp_pricelist = False
            rec.ks_woo_sp_pricelist = False
            instance = rec.ks_wc_instance
            if instance:
                regular_price_list = self.env['product.pricelist.item'].search(
                    [('pricelist_id', '=', instance.ks_woo_regular_pricelist.id),
                     ('product_id', '=', rec.ks_product_variant.id)], limit=1)
                rec.ks_woo_rp_pricelist = regular_price_list.id
                sale_price_list = self.env['product.pricelist.item'].search(
                    [('pricelist_id', '=', instance.ks_woo_sale_pricelist.id),
                     ('product_id', '=', rec.ks_product_variant.id)], limit=1)
                rec.ks_woo_sp_pricelist = sale_price_list.id

    @api.depends('ks_length', 'ks_width', 'ks_height')
    def _ks_compute_volume(self):
        for rec in self:
            rec.ks_volume = rec.ks_length * rec.ks_width * rec.ks_height

    def open_regular_pricelist_rules_data(self):
        """
        :return: The tree view for the regular pricelist item
        """
        self.ensure_one()
        domain = [('product_id', '=', self.ks_product_variant.id if self.ks_product_variant.id else 0),
                  ('currency_id', '=', self.ks_wc_instance.ks_woo_currency.id),
                  ('pricelist_id', '=', self.ks_wc_instance.ks_woo_regular_pricelist.id)
                  ]
        return {
            'name': _('Price Rules'),
            'view_mode': 'form',
            'views': [(self.env.ref('product.product_pricelist_item_tree_view_from_product').id, 'tree'),
                      (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
        }

    def open_sale_pricelist_rules_data(self):
        """
        :return: The tree view for the sale pricelist
        """
        self.ensure_one()
        domain = [('product_id', '=', self.ks_product_variant.id if self.ks_product_variant.id else 0),
                  ('currency_id', '=', self.ks_wc_instance.ks_woo_currency.id),
                  ('pricelist_id', '=', self.ks_wc_instance.ks_woo_sale_pricelist.id)
                  ]
        return {
            'name': _('Price Rules'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('product.product_pricelist_item_tree_view_from_product').id, 'tree'),
                      (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain
        }

    def ks_woo_post_product_variant(self, data, instance, tmpl_id):
        try:
            wc_api = instance.ks_woo_api_authentication()
            product_data_response = wc_api.post("products/%s/variations" % tmpl_id,
                                                data)
            if product_data_response.status_code in [200, 201]:
                product_data = product_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="product_variant",
                                                                   instance=instance,
                                                                   operation_flow="odoo_to_woo",
                                                                   woo_id=product_data.get("id", 0),
                                                                   layer_model="ks.woo.product.variant",
                                                                   message="Create of product variant Successful")
                return product_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="product_variant",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.variant",
                                                                   message=str(product_data_response.text))
        except ConnectionError:
            raise Exception("Couldn't Connect the Instance at time of Customer Syncing !! Please check the network "
                            "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="product_variant",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.variant",
                                                               message=str(e))

    def ks_update_woo_product_variant(self, product_tmpl_id, variant_record_id, data, instance):
        try:
            wc_api = instance.ks_woo_api_authentication()
            woo_pro_variant_response = wc_api.put("products/%s/variations/%s" % (product_tmpl_id, variant_record_id),
                                                  data)
            if woo_pro_variant_response.status_code in [200, 201]:
                product_data = woo_pro_variant_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_woo",
                                                                   status="success",
                                                                   type="product_variant",
                                                                   instance=instance,
                                                                   operation_flow="odoo_to_woo",
                                                                   woo_id=product_data.get("id", 0),
                                                                   layer_model="ks.woo.product.variant",
                                                                   message="Update of product variant Successful")
                return product_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="product_variant",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.variant",
                                                                   message=str(woo_pro_variant_response.text))
        except ConnectionError:
            raise Exception("Couldn't Connect the Instance at time of Customer Syncing !! Please check the network "
                            "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="product_variant",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.variant",
                                                               message=str(e))

    def ks_manage_prepare_variant(self, odoo_product, layer_product, instance, operation=False):
        """
        :param odoo_product: product.template()
        :param layer_product: ks.woo.product.template()
        :param instance: ks.woo.connector.instance()
        :return: ks.woo.product.variants
        """
        try:
            if odoo_product and layer_product:
                variants = odoo_product.product_variant_ids
                variant_prepared = None
                for variant in variants:
                    variant_prepared = variant.ks_product_variant.filtered(lambda x: x.ks_wc_instance.id == instance.id)
                    data = self.ks_map_prepare_variant_data(variant, layer_product, instance)
                    if variant_prepared:
                        variant_prepared.write(data)
                        self.env['product.product'].ks_manage_price_to_export(variant,
                                                                              instance)
                    else:
                        if operation == 'update':
                            data["ks_active"] = False
                        data = self.ks_map_prepare_variant_data(variant, layer_product, instance)
                        variant_prepared = self.create(data)
                        self.env['product.product'].ks_manage_price_to_export(variant,
                                                                              instance)
                    if variant.image_1920:
                        image_data = {
                            "ks_name": variant.name,
                            "ks_wc_image_id": '',
                            "ks_image_name": variant.name + str(variant.id),
                            "ks_wc_variant_id": variant_prepared.id,
                            "ks_image": variant.image_1920
                        }
                        if variant_prepared.ks_wc_image_ids:
                            variant_prepared.ks_wc_image_ids.unlink()
                        variant_image = variant_prepared.ks_wc_image_ids.create(image_data)
        except Exception as e:
            if len(variant_prepared) >= 2:
                raise Exception("You cannot export this product because you have added wrong type of attributes "
                                "variants !  ")
            else:
                raise e

    def ks_map_prepare_variant_data(self, odoo_variant, layer_product, instance):
        """
        :param odoo_variant: product.product()
        :param layer_product: ks.woo.product.template()
        :param instance: ks.woo.connector.instance()
        :return:variant layer compatible data
        """
        data = {
            "ks_wc_instance": instance.id,
            "ks_product_variant": odoo_variant.id,
            "ks_wc_product_tmpl_id": layer_product.id,
            "ks_length": odoo_variant.ks_length,
            "ks_height": odoo_variant.ks_height,
            "ks_width": odoo_variant.ks_width,
            "ks_weight": odoo_variant.weight,
            "ks_active": True,
            "ks_default_code": odoo_variant.default_code,
            "ks_company_id": instance.ks_company_id.id,
        }
        return data

    # Todo
    def ks_woo_get_product_variant(self, instance, tmpl_id, variation_id):
        try:
            wc_api = instance.ks_woo_api_authentication()
            product_data_response = wc_api.post("products/%s/variations/%s" % (tmpl_id, variation_id))
            if product_data_response.status_code in [200, 201]:
                product_data = product_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="product_variant",
                                                                   instance=instance,
                                                                   operation_flow="woo_to_odoo",
                                                                   woo_id=product_data.get("id", 0),
                                                                   layer_model="ks.woo.product.variant",
                                                                   message="Fetch of product variant Successful")
                return product_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="product_variant",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.variant",
                                                                   message=str(product_data_response.text))
        except ConnectionError:
            raise Exception("Couldn't Connect the Instance at time of Customer Syncing !! Please check the network "
                            "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="product_variant",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.variant",
                                                               message=str(e))

    def ks_woo_get_all_product_variant(self, instance, templ_id, include=False):
        """
        :param instance: ks.woo.connector.instance()
        :param templ_id: woo product id
        :param include: specific ids
        :return: json response
        """
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = []
        if include:
            include = [str(include) for include in include]
            include = ",".join(include)
            params = {'per_page': per_page,
                      'page': page,
                      'include': include}
        else:
            params = {'per_page': per_page, 'page': page}
        try:
            while multi_api_call:
                wc_api = instance.ks_woo_api_authentication()
                variant_data_response = wc_api.get("products/%s/variations" % templ_id, params=params)
                if variant_data_response.status_code in [200, 201]:
                    all_retrieved_data.extend(variant_data_response.json())

                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="product_variant",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.product.variant",
                                                                       message=str(variant_data_response.text))

                total_api_calls = variant_data_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                    params.update({'page': page})
                else:
                    multi_api_call = False

        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="product_variant",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.variant",
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="product_variant",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.variant",
                                                               message="Fetch of product variant Successful")
            return all_retrieved_data

    def get_all_variants_data(self, all_odoo_variations):
        """
        :param all_odoo_variations: [product.product()]
        :return: data for all varaints
        """
        data = []
        for var in all_odoo_variations:
            var_data = {}
            var_data["variant_id"] = var.id
            var_data["values"] = []
            for attr in var.product_template_attribute_value_ids:
                var_data['values'].append({"attribute_id": attr.attribute_id.id,
                                           "attribute_name": attr.attribute_id.name,
                                           "attribute_value_id": attr.product_attribute_value_id.id,
                                           "attribute_value_name": attr.product_attribute_value_id.name})

            data.append(var_data)

        return data

    def ks_manage_variations_import(self, instance, odoo_main_product, woo_layer_product, product_json_data):
        """
        :param instance: ks.woo.connector.instance()
        :param odoo_main_product: product.temnplate()
        :param product_json_data: woo product json data
        :return: ks.woo.product.variant()
        """
        all_odoo_variations = odoo_main_product.product_variant_ids
        all_variants_data = self.get_all_variants_data(all_odoo_variations)
        all_woo_variations = self.ks_woo_get_all_product_variant(instance, product_json_data.get("id"),
                                                                 include=product_json_data.get("variations"))
        variant_exist = None
        for index, variant in enumerate(all_woo_variations):
            variant_exist = self.search([('ks_wc_instance', '=', instance.id),
                                         ('ks_woo_variant_id', '=', variant.get("id"))])
            if variant_exist:
                # Run update command here
                layer_data = self.ks_map_variant_data_for_layer(variant, all_variants_data, instance, woo_layer_product)
                variant_exist.write(layer_data)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(variant,
                                                                                 variant_exist,
                                                                                 "ks_woo_variant_id")
            else:
                layer_data = self.ks_map_variant_data_for_layer(variant, all_variants_data, instance, woo_layer_product)
                variant_exist = self.create(layer_data)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(variant,
                                                                                 variant_exist,
                                                                                 "ks_woo_variant_id")
            if instance.ks_sync_price:
                variant_exist.ks_product_variant.ks_manage_price_to_import(instance, variant.get("regular_price"),
                                                                           variant.get("sale_price"))
        not_active_variant = odoo_main_product.ks_product_template.ks_wc_variant_ids.filtered(
            lambda x: x.ks_woo_variant_id not in product_json_data.get("variations"))
        try:
            for var in not_active_variant:
                var.write({"ks_active": False})

        except Exception as e:
            _logger.info(str(e))

        return variant_exist

    def ks_find_variant_match(self, all_variants_data, attribute):
        """
        :param all_variants_data: odoo variants data
        :param attribute: json woo attribute
        :return:
        """
        for values in all_variants_data:
            flag = 0
            for attr in values['values']:
                for woo_att in attribute:
                    attribute_name = woo_att.get("name")
                    attribute_value = woo_att.get("option")
                    if attribute_name.lower() == attr.get("attribute_name").lower() and attribute_value.lower() == \
                            attr.get("attribute_value_name").lower():
                        flag += 1
                if flag == len(attribute):
                    return values['variant_id']
        return False

    def ks_map_variant_data_for_layer(self, variant, all_variants_data, instance, woo_layer_product):
        """
        :param variant: woo json data
        :param all_variants_data: dict of all attributes and attributes values
        :param instance: ks.woo.connector.instance()
        :param odoo_main_product: product.template()
        :return: ks.woo.product.variant() compatible data
        """
        data = {
            "ks_length": variant['dimensions'].get("length", 0),
            "ks_width": variant['dimensions'].get("width", 0),
            "ks_height": variant['dimensions'].get("height", 0),
            "ks_weight": variant.get("weight", 0),
            "ks_wc_instance": instance.id,
            "ks_woo_variant_id": variant.get("id"),
            "ks_wc_product_tmpl_id": woo_layer_product.id,
            "ks_woo_description": variant.get("description", ''),
            "ks_default_code": variant.get("sku", ''),
            "ks_company_id": instance.ks_company_id.id,
        }
        attribute = variant['attributes']
        find_variant = self.ks_find_variant_match(all_variants_data, attribute)
        if find_variant:
            prodcut_variant = self.env['product.product'].browse(find_variant)
            if prodcut_variant:
                prodcut_variant.write({
                    "weight": variant.get('weight') or '',
                    "ks_length": variant.get('dimensions').get('length') or '',
                    "ks_height": variant.get('dimensions').get('height') or '',
                    "ks_width": variant.get('dimensions').get('width') or '',
                    "volume": float(variant.get('dimensions').get('length') or 0.0) * float(
                        variant.get('dimensions').get('height') or 0.0) * float(
                        variant.get('dimensions').get('width') or 0.0),
                    "default_code": variant.get("sku", '')
                })
                if instance and instance.ks_want_maps:
                    if variant.get("meta_data"):
                        product_maps = instance.ks_meta_mapping_ids.search([('ks_wc_instance', '=', instance.id),
                                                                            ('ks_active', '=', True),
                                                                            (
                                                                            'ks_model_id.model', '=', 'product.product')
                                                                            ])
                        for map in product_maps:
                            odoo_field = map.ks_fields.name
                            json_key = map.ks_key
                            for meta_data in variant.get("meta_data"):
                                if meta_data.get("key", '') == json_key:
                                    if odoo_field == 'barcode' and len(meta_data.get("value")) == 0:
                                        meta_data.update({'value': False})
                                    prodcut_variant.update({
                                        odoo_field: meta_data.get("value", '')
                                    })
            data.update({"ks_product_variant": find_variant, "ks_active": True})
        else:
            data.update({"ks_active": False})
        return data

    def ks_prepare_product_variant_stock_to_export(self, product_config=False):
        variant = self.ks_product_variant
        server_action = product_config.get("server_action") if product_config else False
        stock_qty = self.env['product.product'].ks_get_stock_quantity(self.ks_wc_instance.ks_warehouse,
                                                                      variant,
                                                                      self.ks_wc_instance.ks_stock_field_type.name)
        data = {}
        data.update({
            "manage_stock": True,
            "stock_quantity": stock_qty,
            "stock_status": "instock" if stock_qty > 0 else "outofstock"
        })
        return data

    def ks_prepare_product_variant_to_export(self, instance, product_config=False):
        variant = self.ks_product_variant
        server_action = product_config.get("server_action") if product_config else False
        stock_qty = self.env['product.product'].ks_get_stock_quantity(self.ks_wc_instance.ks_warehouse,
                                                                      variant,
                                                                      self.ks_wc_instance.ks_stock_field_type.name)
        data = {
            'description': self.ks_woo_description if self.ks_woo_description else '',
            'weight': str(self.ks_weight),
            'dimensions': {
                'length': str(self.ks_length),
                'width': str(self.ks_width),
                'height': str(self.ks_height)
            },
        }
        sale_price = self.ks_wc_instance.ks_woo_sale_pricelist.ks_get_product_price(variant, instance,
                                                                                    self.ks_wc_product_tmpl_id)
        if server_action:
            if product_config["price"] == True:
                data.update(
                    {
                        "regular_price": str(
                            self.ks_wc_instance.ks_woo_regular_pricelist.ks_get_product_price(variant, instance,
                                                                                              self.ks_wc_product_tmpl_id)),
                        "sale_price": str(sale_price) if sale_price else '',
                    }
                )
            if product_config['stock'] == True:
                data.update({
                    "manage_stock": True,
                    "stock_quantity": stock_qty,
                    "stock_status": "instock" if stock_qty > 0 else "outofstock",
                    "sku": self.ks_default_code if self.ks_default_code else ''
                })

            if product_config["image"] == True and self.ks_wc_image_ids and product_config['variant_image']:
                data.update({"image": self.ks_wc_image_ids.ks_prepare_variant_images_for_woo()})


        else:
            data.update({
                "manage_stock": True,
                "stock_quantity": stock_qty,
                "stock_status": "instock" if stock_qty > 0 else "outofstock",
                "regular_price": str(
                    self.ks_wc_instance.ks_woo_regular_pricelist.ks_get_product_price(variant, instance,
                                                                                      self.ks_wc_product_tmpl_id)),
                "sale_price": str(sale_price) if sale_price else '',
                "sku": variant.default_code if variant.default_code else ''
            })
            if self.ks_wc_image_ids and instance.ks_export_image_variation:
                data.update({"image": self.ks_wc_image_ids.ks_prepare_variant_images_for_woo()})
        data.update({"attributes": self.ks_manage_variant_attributes(self.ks_product_variant)})

        if instance and instance.ks_want_maps:
            meta = {"meta_data": []}
            product_maps = instance.ks_meta_mapping_ids.search([('ks_wc_instance', '=', instance.id),
                                                                ('ks_active', '=', True),
                                                                ('ks_model_id.model', '=', 'product.product')
                                                                ])
            for map in product_maps:
                json_key = map.ks_key
                odoo_field = map.ks_fields
                query = """
                    select coalesce(%s, '') from product_product where id = %s
                """ % (odoo_field.name, variant.id)
                self.env.cr.execute(query)
                results = self.env.cr.fetchall()
                if results:
                    meta['meta_data'].append({
                        "key": json_key,
                        "value": str(results[0][0])
                    })
                    data.update(meta)
        return data

    def ks_manage_variant_attributes(self, variant):
        attribute_data = []
        if variant.product_template_attribute_value_ids:
            for attribute_value in variant.product_template_attribute_value_ids:
                # Manage the syncing of already prepared
                value_layer_exist = self.env['ks.woo.pro.attr.value'].check_if_already_prepared(self.ks_wc_instance,
                                                                                                attribute_value.product_attribute_value_id)
                if value_layer_exist:
                    attribute_data.append({
                        "id": value_layer_exist.ks_woo_attribute_id,
                        "name": value_layer_exist.ks_name,
                        "option": attribute_value.product_attribute_value_id.name
                    })
                else:
                    attribute_data.append({
                        "id": 0,
                        "name": attribute_value.attribute_id.name,
                        "option": attribute_value.product_attribute_value_id.name
                    })
        return attribute_data

    def ks_manage_woo_product_variant_export(self, instance, queue_record=False, product_config=False):
        for rec in self:
            if rec.ks_active and rec.ks_product_variant:
                try:
                    product_exported = rec.ks_woo_variant_id
                    if queue_record and queue_record.ks_model == 'stock':
                        data = rec.ks_prepare_product_variant_stock_to_export(product_config)
                    else:
                        data = rec.ks_prepare_product_variant_to_export(instance, product_config)

                    if product_exported:
                        product_data_response = self.ks_update_woo_product_variant(
                            rec.ks_wc_product_tmpl_id.ks_woo_product_id,
                            product_exported, data, instance)
                        if product_data_response:
                            self.env['ks.woo.connector.instance'].ks_woo_update_the_response(product_data_response,
                                                                                             rec,
                                                                                             'ks_woo_variant_id')
                    else:

                        product_data_response = self.ks_woo_post_product_variant(data, instance,
                                                                                 rec.ks_wc_product_tmpl_id.ks_woo_product_id)
                        if product_data_response:
                            self.env['ks.woo.connector.instance'].ks_woo_update_the_response(product_data_response,
                                                                                             rec,
                                                                                             'ks_woo_variant_id')

                        else:
                            raise ValidationError("Fatal Error")
                except Exception as e:
                    _logger.error(traceback.format_exc())
                    if queue_record:
                        queue_record.ks_update_failed_state()


class KsProductVariantInherit(models.Model):
    _inherit = "product.product"

    ks_product_variant = fields.One2many('ks.woo.product.variant', 'ks_product_variant')

    def ks_manage_price_to_export(self, product_variant, instance):
        regular_price_list = instance.ks_woo_regular_pricelist
        ks_woo_product_template = product_variant.product_tmpl_id.ks_product_template.filtered(
            lambda l: l.ks_wc_instance == instance)
        sale_price_list = instance.ks_woo_sale_pricelist
        all_regular_price_list = instance.ks_woo_pricelist_ids.filtered(
            lambda l: l.ks_wc_instance == instance and (l.ks_wc_regular_pricelist))
        all_sale_price_list = instance.ks_woo_pricelist_ids.filtered(
            lambda l: l.ks_wc_instance == instance and (l.ks_wc_sale_pricelist))

        if ks_woo_product_template.ks_woo_product_type == 'simple':
            for price_list in all_regular_price_list:
                if ks_woo_product_template and ks_woo_product_template.ks_woo_product_id:
                    price = instance.ks_woo_regular_pricelist.ks_get_product_price(product_variant, instance,
                                                                                   ks_woo_product_template)
                    price_list.ks_set_product_price(product_id=product_variant.id, price=price,
                                                    main_price_list=regular_price_list)
                else:
                    price_list.ks_set_product_price(product_id=product_variant.id, price=product_variant.lst_price,
                                                    main_price_list=regular_price_list)

            for price_list in all_sale_price_list:
                if ks_woo_product_template and ks_woo_product_template.ks_woo_product_id:
                    price = instance.ks_woo_sale_pricelist.ks_get_product_price(product_variant, instance,
                                                                                ks_woo_product_template)
                    price_list.ks_set_product_price(product_id=product_variant.id, price=price,
                                                    main_price_list=sale_price_list)
                else:
                    price_list.ks_set_product_price(product_id=product_variant.id, price=0,
                                                    main_price_list=sale_price_list)
        else:

            for price_list in all_regular_price_list:
                if ks_woo_product_template and product_variant.ks_product_variant.filtered(
                        lambda l: l.ks_company_id.id == instance.ks_company_id.id and l.ks_wc_instance.id == instance.id).ks_woo_variant_id:
                    price = instance.ks_woo_regular_pricelist.ks_get_product_price(product_variant, instance,
                                                                                   ks_woo_product_template)
                    price_list.ks_set_product_price(product_id=product_variant.id, price=price,
                                                    main_price_list=regular_price_list)
                # elif instance.ks_no_variant == True:
                #     price_list.ks_set_product_price(product_id=product_variant.id, price=product_variant.ks_product_template.ks_woo_regular_price,
                #                                     main_price_list=regular_price_list)
                #     max_id = max(price_list.item_ids.ids)
                #     product_variant.ks_product_variant.ks_woo_rp_pricelist = price_list.item_ids.filtered(
                #         lambda x: x.id == max_id)
                else:
                    price_list.ks_set_product_price(product_id=product_variant.id, price=product_variant.lst_price,
                                                    main_price_list=regular_price_list)
                    max_id = max(price_list.item_ids.ids)
                    product_variant.ks_product_variant.ks_woo_rp_pricelist = price_list.item_ids.filtered(
                        lambda x: x.id == max_id)

            for price_list in all_sale_price_list:
                if ks_woo_product_template and product_variant.ks_product_variant.filtered(
                        lambda l: l.ks_company_id.id == instance.ks_company_id.id and l.ks_wc_instance.id == instance.id).ks_woo_variant_id:
                    price = instance.ks_woo_sale_pricelist.ks_get_product_price(product_variant, instance,
                                                                                ks_woo_product_template)
                    price_list.ks_set_product_price(product_id=product_variant.id, price=price,
                                                    main_price_list=sale_price_list)
                # elif instance.ks_no_variant == True:
                #     price_list.ks_set_product_price(product_id=product_variant.id, price=product_variant.ks_product_template.ks_woo_sale_price,
                #                                     main_price_list=regular_price_list)
                #     max_id = max(price_list.item_ids.ids)
                #     product_variant.ks_product_variant.ks_woo_rp_pricelist = price_list.item_ids.filtered(
                #         lambda x: x.id == max_id)
                else:
                    price_list.ks_set_product_price(product_id=product_variant.id, price=0,
                                                    main_price_list=sale_price_list)
                    max_id = max(price_list.item_ids.ids)
                    product_variant.ks_product_variant.ks_woo_sp_pricelist = price_list.item_ids.filtered(
                        lambda x: x.id == max_id)

    def ks_manage_price_to_import(self, instance, regular_price=0, sale_price=0):
        regular_price = float(regular_price or 0.0) if instance.ks_sync_price else 0.0
        sale_price = float(sale_price or 0.0) if instance.ks_sync_price else 0.0
        regular_price_list = instance.ks_woo_regular_pricelist
        sale_price_list = instance.ks_woo_sale_pricelist
        all_regular_price_list = instance.ks_woo_pricelist_ids.filtered(
            lambda l: l.ks_wc_instance == instance and (l.ks_wc_regular_pricelist))
        all_sale_price_list = instance.ks_woo_pricelist_ids.filtered(
            lambda l: l.ks_wc_instance == instance and (l.ks_wc_sale_pricelist))
        for price_list in all_regular_price_list:
            price_list.ks_set_product_price(product_id=self.id, price=regular_price, main_price_list=regular_price_list)
        for price_list in all_sale_price_list:
            price_list.ks_set_product_price(product_id=self.id, price=sale_price, main_price_list=sale_price_list)
