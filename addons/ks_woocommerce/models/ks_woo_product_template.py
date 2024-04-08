import datetime
import logging
import traceback
import json

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class KsWooProductTemplate(models.Model):
    _name = "ks.woo.product.template"
    _rec_name = "ks_product_template"
    _description = "Woo Product Model"

    ks_woo_description = fields.Html('Description', help="Message displayed as product description on WooCommerce",
                                     translate=True)
    ks_woo_short_description = fields.Html('Short Description',
                                           help="Message displayed as product short description on WooCommerce",
                                           translate=True)
    ks_published = fields.Boolean('Woo Status',
                                  copy=False,
                                  help="""Woo Status: If enabled that means the product is published on the WooCommerce 
                                       Instance.""")
    ks_woo_product_type = fields.Selection([('simple', 'Simple Product'), ('grouped', 'Grouped Product'),
                                            ('variable', 'Variable Product')], readonly=True,
                                           string='Woo Product Type', store=True, default="simple",
                                           help="Displays WooCommerce Product Type")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", readonly=True,
                                     help=_("WooCommerce Connector Instance reference"), ondelete='cascade')
    ks_woo_product_id = fields.Integer('Woo Product ID',
                                       help=_("the record id of the particular record defied in the Connector"),
                                       readonly=True)
    ks_date_created = fields.Datetime('Date Created', help=_("The date on which the record is created on the Connected"
                                                             " Connector Instance"), readonly=True)
    ks_date_updated = fields.Datetime('Date Updated', help=_("The latest date on which the record is updated on the"
                                                             " Connected Connector Instance"), readonly=True)
    ks_product_template = fields.Many2one('product.template', 'Odoo Product Template', readonly=True,
                                          ondelete='cascade', help="Displays Odoo Linked Product Template Name")
    ks_name = fields.Char(string="Name", related="ks_product_template.name")
    ks_product_product = fields.Many2one('product.product', 'Odoo Product Variant',
                                         related="ks_product_template.product_variant_id",
                                         readonly=True)
    ks_wc_tag_ids = fields.Many2many('ks.woo.product.tag', string='Tags',
                                     domain="[('ks_woo_tag_id', '!=', 0), "
                                            "('ks_wc_instance', '=', ks_wc_instance)]",
                                     help="Displays WooCommerce Tags")

    ks_wc_variant_ids = fields.One2many('ks.woo.product.variant', 'ks_wc_product_tmpl_id', string='Variants',
                                        readonly=True)

    ks_woo_rp_pricelist = fields.Many2one("product.pricelist.item", compute="_ks_calculate_pricelists",
                                          string="Regular Pricelist", help="Displays WooCommerce Regular Price")
    ks_woo_sp_pricelist = fields.Many2one("product.pricelist.item", compute="_ks_calculate_pricelists",
                                          string="Sale Pricelist", help=" Displays WooCommerce Sale Price")
    ks_woo_regular_price = fields.Char('Woo Regular Price', compute="ks_update_woo_regular_price", default="0.0")
    ks_woo_sale_price = fields.Char('Woo Sale Price', compute='ks_update_woo_sale_price', default="0.0")

    ks_wc_image_ids = fields.One2many('ks.woo.product.images', 'ks_wc_template_id', string='Images', readonly=True)
    ks_mapped = fields.Boolean(string="Manual Mapping", readonly=True)
    profile_image = fields.Many2one("ks.woo.product.images", string="Profile Image")

    ks_sync_date = fields.Datetime('Modified On', readonly=True,
                                   help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On', readonly=True)
    ks_sync_status = fields.Boolean('Sync Status', compute='sync_update', default=False)
    ks_company_id = fields.Many2one('res.company', string="Company",
                                    default=lambda self: self.ks_wc_instance.ks_company_id.id,
                                    required=True, readonly=True, help=" Shows the name of the company")

    def non_clickable_action(self):
        pass

    @api.depends('ks_wc_instance', 'ks_wc_instance.ks_woo_regular_pricelist', 'ks_wc_instance.ks_woo_sale_pricelist',
                 'ks_product_template.product_variant_id')
    @api.model
    def _ks_calculate_pricelists(self):
        for rec in self:
            rec.ks_woo_rp_pricelist = False
            rec.ks_woo_sp_pricelist = False
            if rec.ks_woo_product_type == "simple":
                variant = rec.ks_product_template.product_variant_id
                instance = rec.ks_wc_instance
                if instance and variant:
                    regular_price_list = self.env['product.pricelist.item'].search(
                        [('pricelist_id', '=', instance.ks_woo_regular_pricelist.id),
                         ('product_id', '=', variant.id)], limit=1)
                    rec.ks_woo_rp_pricelist = regular_price_list.id
                    sale_price_list = self.env['product.pricelist.item'].search(
                        [('pricelist_id', '=', instance.ks_woo_sale_pricelist.id),
                         ('product_id', '=', variant.id)], limit=1)
                    rec.ks_woo_sp_pricelist = sale_price_list.id

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

    def ks_update_woo_regular_price(self):
        """
        Updates the Regular price from the pricelist
        :return: None
        """
        for rec in self:
            rec.ks_woo_regular_price = str(self.env['product.pricelist.item'].search(
                [('pricelist_id', '=', rec.ks_wc_instance.ks_woo_regular_pricelist.id),
                 ('product_id', '=', rec.ks_product_product.id)], limit=1).price) if self.env[
                'product.pricelist.item'].search([('pricelist_id', '=', rec.ks_wc_instance.ks_woo_regular_pricelist.id),
                                                  ('product_id', '=', rec.ks_product_product.id)],
                                                 limit=1).price else '0.0'

    def ks_update_woo_sale_price(self):
        """
        Updates the Sale price from the pricelist
        :return: None
        """
        for rec in self:
            rec.ks_woo_sale_price = str(self.env['product.pricelist.item'].search(
                [('pricelist_id', '=', rec.ks_wc_instance.ks_woo_sale_pricelist.id),
                 ('product_id', '=', rec.ks_product_product.id)], limit=1).price) if self.env[
                'product.pricelist.item'].search([('pricelist_id', '=', rec.ks_wc_instance.ks_woo_sale_pricelist.id),
                                                  ('product_id', '=', rec.ks_product_product.id)],
                                                 limit=1).price else '0.0'

    def open_regular_pricelist_rules_data(self):
        """
        :return: The tree view for the regular pricelist item
        """
        self.ensure_one()
        if self.ks_woo_product_type == 'simple':
            domain = [('product_id', '=',
                       self.ks_product_template.product_variant_id.id if self.ks_product_template.product_variant_id.id else 0),
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

    def action_show_variants(self):
        action = {
            'domain': [('id', 'in', self.ks_wc_variant_ids.ids)],
            'name': 'WooCommere Variants',
            'view_mode': 'tree,form',
            'res_model': 'ks.woo.product.variant',
            'type': 'ir.actions.act_window',
        }
        return action

    def open_sale_pricelist_rules_data(self):
        """
        :return: The tree view for the sale pricelist
        """
        self.ensure_one()
        domain = [('product_id', '=',
                   self.ks_product_template.product_variant_id.id if self.ks_product_template.product_variant_id.id else 0),
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

    @api.depends('ks_wc_instance')
    def _ks_calculate_prices(self):
        for rec in self:
            if rec.ks_product_product and rec.ks_woo_product_type == "simple":
                variant = rec.ks_product_product
                instance = rec.ks_wc_instance
                if instance:
                    regular_price = self.env['product.pricelist.item'].search(
                        [('pricelist_id', '=', instance.ks_woo_regular_pricelist.id),
                         ('product_id', '=', variant.id)], limit=1).price
                    rec.ks_woo_regular_price = regular_price
                    sale_price = self.env['product.pricelist.item'].search(
                        [('pricelist_id', '=', instance.ks_woo_sale_pricelist.id),
                         ('product_id', '=', variant.id)], limit=1).price
                    rec.ks_woo_sale_price = sale_price
            else:
                rec.ks_woo_sale_price = '0'
                rec.ks_woo_regular_price = '0'

    def compute_sync_status(self):
        if self:
            for rec in self:
                if not rec.ks_date_created and not rec.ks_date_updated:
                    rec.ks_sync_states = False

                elif rec.ks_date_updated >= rec.write_date \
                        or (abs(rec.ks_date_updated - rec.write_date).total_seconds() / 60) < 2:
                    rec.ks_sync_states = True

                else:
                    rec.ks_sync_states = False

    def action_publish(self):
        try:
            for rec in self:
                if rec.ks_woo_product_id:
                    json_data = {
                        "status": 'publish' if not rec.ks_published else 'draft'
                    }
                    product_data = self.ks_woo_update_product(rec.ks_woo_product_id, json_data, rec.ks_wc_instance)
                    rec.ks_published = not rec.ks_published if product_data else rec.ks_published

        except Exception as e:
            _logger.info(str(e))

    def ks_woo_get_product(self, product_id, instance):
        try:
            wc_api = instance.ks_woo_api_authentication()
            product_data_response = wc_api.get("products/%s" % product_id)
            if product_data_response.status_code in [200, 201]:
                product_data = product_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="product",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=product_data.get("id", 0),
                                                                   layer_model="ks.woo.product.template",
                                                                   message="Fetch of Products successful")
                return product_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="product",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.template",
                                                                   message=str(product_data_response.text))
        except ConnectionError:
            raise Exception("Couldn't Connect the Instance at time of Customer Syncing !! Please check the network "
                            "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="product",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.template",
                                                               message=str(e))

    def ks_woo_get_all_products(self, instance, include=False, date_before=False, date_after=False):
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = []
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
            params = {'per_page': per_page,
                      'page': page}
        try:
            while multi_api_call:
                wc_api = instance.ks_woo_api_authentication()
                product_data_response = wc_api.get("products", params=params)
                if product_data_response.status_code in [200, 201]:
                    all_retrieved_data.extend(product_data_response.json())
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="product",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.product.template",
                                                                       message=str(product_data_response.text))
                total_api_calls = product_data_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                    params.update({
                        'page': page,
                    })
                else:
                    multi_api_call = False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="product",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.template",
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="product",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance,
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.template",
                                                               message="Fetch of Products successful")
            return all_retrieved_data

    def ks_woo_update_product(self, product_tmpl_id, data, instance):
        try:
            wc_api = instance.ks_woo_api_authentication()
            woo_product_tmpl_response = wc_api.put("products/%s" % product_tmpl_id, data)
            if woo_product_tmpl_response.status_code in [200, 201]:
                product_data = woo_product_tmpl_response.json()
                return product_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="product",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=self.ks_product_template.id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.template",
                                                                   message=str(woo_product_tmpl_response.text))
        except ConnectionError:
            raise Exception("Couldn't Connect the Instance at time of Customer Syncing !! Please check the network "
                            "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            _logger.error(traceback.format_exc())
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="product",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               ks_record_id=self.ks_product_template.id,
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.template",
                                                               message=str(e))

    def ks_woo_post_product_template(self, data, instance):
        try:
            wc_api = instance.ks_woo_api_authentication()
            product_data_response = wc_api.post("products", data)
            if product_data_response.status_code in [200, 201]:
                product_data = product_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="product",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=self.ks_product_template.id,
                                                                   woo_id=product_data.get("id", 0),
                                                                   layer_model="ks.woo.product.template",
                                                                   message="Create of Products successful")
                return product_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="product",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=self.ks_product_template.id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.product.template",
                                                                   message=str(product_data_response.text))
        except ConnectionError:
            raise Exception("Couldn't Connect the Instance at time of Product Syncing !! Please check the network "
                            "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="product",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               ks_record_id=self.ks_product_template.id,
                                                               woo_id=0,
                                                               layer_model="ks.woo.product.template",
                                                               message=str(e))

    def create_woo_product(self, instance, product_json_data, odoo_main_product, export_to_woo=False):
        if odoo_main_product.type == "product":
            layer_product_data = self.ks_map_product_template_data_for_layer(instance, product_json_data,
                                                                             odoo_main_product)
            try:
                woo_product = self.create(layer_product_data)
                return woo_product
            except Exception as e:
                _logger.info(str(e))

    def update_woo_product(self, instance, product_exist, product_json_data, update_to_woo=False):
        if product_exist.ks_product_template.type == "product":
            layer_product_data = self.ks_map_product_template_data_for_layer(instance, product_json_data,
                                                                             product_exist.ks_product_template)
            try:
                product_exist.write(layer_product_data)
                return product_exist
            except Exception as e:
                _logger.info(str(e))

    def ks_action_woo_import_product(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance and e.ks_woo_product_id)
                if len(records):
                    for dat in records:
                        json_data = [self.ks_woo_get_product(dat.ks_woo_product_id, dat.ks_wc_instance)]
                        if json_data[0]:
                            self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(data=json_data,
                                                                                            instance=dat.ks_wc_instance)
                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Products Records enqueued in Queue 
                                                                           Please refer Queue and logs for further details
                                                                           ''')

            except Exception as e:
                raise e

        else:
            try:
                self.ensure_one()
                if self.ks_woo_product_id and self.ks_wc_instance:
                    json_data = self.ks_woo_get_product(self.ks_woo_product_id, self.ks_wc_instance)
                    if json_data:
                        product = self.ks_manage_woo_product_template_import(self.ks_wc_instance, json_data)

                    return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                           "Action Performed. Please refer logs for further details.")

            except Exception as e:
                raise e

    def ks_action_woo_export_product(self, product_config=False):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance)
                if len(records):
                    self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(records=records,
                                                                                    product_config=product_config)
                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Product Records enqueued in Queue 
                                                                              Please refer Queue and logs for further details
                                                                              ''')
            except Exception as e:
                _logger.info(str(e))

        else:
            try:
                self.ensure_one()
                self.ks_manage_woo_product_template_export(self.ks_wc_instance, product_config=product_config)

            except Exception as e:
                _logger.info(str(e))
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_manage_variant_images(self, odoo_product, instance, woo_json):
        """
        :param odoo_product: product.template()
        :param woo_json: woocommerce json data
        :return:
        """
        try:
            if odoo_product and woo_json:
                image_json_data = woo_json.get("images", [])
                if image_json_data:
                    main_image_url = image_json_data[0]['src']
                    if main_image_url:
                        image = self.env['ks.common.product.images'].get_image_from_url(main_image_url)
                        odoo_product.write({'image_1920': image})
                variant_ids = odoo_product.product_variant_ids
                woo_variants = woo_json.get("variations", "")
                if woo_variants:
                    for index, id in enumerate(woo_variants):
                        woo_variant = self.ks_woo_get_product(id, instance)
                        if woo_variant.get("images"):
                            image = woo_variant.get('images')[0]['src']
                            if image:
                                bin_image = self.env['ks.common.product.images'].get_image_from_url(image)
                                variant_ids[index].write({"image_1920": bin_image})
        except Exception as e:
            _logger.info(str(e))

    def ks_auto_export_wc_product(self, instance):
        woo_products = []
        ks_wc_instance = self.env['ks.woo.connector.instance'].browse(instance)
        woo_all_products = self.env['product.template'].search([('ks_product_template', '=', False)])
        for product in woo_all_products:
            layer_product = self.create_woo_record(ks_wc_instance, product)
            woo_products.append(layer_product)
        self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=ks_wc_instance,
                                                                        records=woo_products)

    def ks_auto_update_wc_product(self, instance):
        woo_products = []
        ks_wc_instance = self.env['ks.woo.connector.instance'].browse(instance)
        woo_all_products = self.env['ks.woo.product.template'].search([('ks_wc_instance', '=', instance)])
        for product in woo_all_products:
            layer_product = self.update_woo_record(ks_wc_instance, product.ks_product_template)
            woo_products.append(layer_product)
        self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instance=ks_wc_instance,
                                                                        records=woo_products)

    def ks_manage_woo_product_template_import(self, instance, product_json_data, odoo_main_product=False,
                                              queue_record=False):
        """
        :param instance: Woo Instance ks.woo.connector.instance()
        :param product_json_data: json data for product template
        :param queue_record: queue handler
        :return: managed ks.woo.product.template()
        """
        try:
            product_exist = self.env['ks.woo.product.template'].search(
                [('ks_wc_instance', '=', instance.id),
                 ('ks_woo_product_id', '=', product_json_data.get("id"))])
            if product_json_data.get("type") == 'simple':
                if product_exist:
                    try:
                        if product_exist.ks_woo_product_type == product_json_data.get("type"):
                            main_product_data = self.ks_map_product_template_data_for_odoo(product_json_data, instance)
                            if instance and instance.ks_want_maps:
                                if 'barcode_check_field' in main_product_data.keys():
                                    product_barcode_exist = self.env['product.product'].search(
                                        [('barcode', '=', main_product_data.get('barcode_check_field'))])
                                    main_product_data.pop('barcode_check_field', None)
                                    if product_barcode_exist:
                                        same_prod_tmpl_id = self.env['ks.woo.product.template'].search(
                                            [('ks_woo_product_id', '=', product_json_data.get('id')),
                                             ('ks_wc_instance', '=', instance.id)]).ks_product_product
                                        if same_prod_tmpl_id.id not in product_barcode_exist.ids:
                                            _logger.error(
                                                f'Product barcode already exist for the product of woo id: {product_json_data.get("id")}.')
                                            self.env.cr.commit()
                                            return False
                            self.env['product.template'].ks_update_product_template(product_exist, main_product_data)
                            if instance.ks_sync_price:
                                product_exist.ks_product_template.product_variant_id.ks_manage_price_to_import(instance,
                                                                                                               product_json_data.get(
                                                                                                                   "regular_price"),
                                                                                                               product_json_data.get(
                                                                                                                   "sale_price"))
                            self.update_woo_product(instance, product_exist, product_json_data)
                            self.env['ks.woo.connector.instance'].ks_woo_update_the_response(product_json_data,
                                                                                             product_exist,
                                                                                             "ks_woo_product_id")
                            if instance.ks_sync_images:
                                self.env['ks.woo.product.images'].ks_update_images_for_odoo(
                                    product_json_data.get("images"),
                                    product=product_exist.id)
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                               ks_model='product.template',
                                                                               ks_layer_model='ks.woo.product.template',
                                                                               ks_message="Product import update success",
                                                                               ks_status="success",
                                                                               ks_type="product",
                                                                               ks_record_id=product_exist.id,
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_woo_id=product_json_data.get(
                                                                                   "id", 0),
                                                                               ks_woo_instance=instance)
                            product_exist.ks_sync_date = datetime.datetime.now()
                            product_exist.ks_last_exported_date = product_exist.ks_sync_date
                            product_exist.sync_update()

                            return product_exist
                        else:
                            if queue_record:
                                queue_record.ks_update_failed_state()
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                               ks_model='product.template',
                                                                               ks_layer_model='ks.woo.product.template',
                                                                               ks_message="Product Type Change, Please delete the odoo side product and perform fresh import",
                                                                               ks_status="failed",
                                                                               ks_type="product",
                                                                               ks_record_id=0,
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_woo_id=product_json_data.get(
                                                                                   "id", 0),
                                                                               ks_woo_instance=instance)
                    except Exception as e:
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message=str(e),
                                                                           ks_status="failed",
                                                                           ks_type="product",
                                                                           ks_record_id=0,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=product_json_data.get(
                                                                               "id", 0),
                                                                           ks_woo_instance=instance)
                        _logger.error('Product Update Operation Failed. ks_record_id = %s, ks_woo_id = %s. Message: %s',
                                      0, product_json_data.get(
                                "id", 0), str(e))
                else:
                    try:
                        if not odoo_main_product:
                            main_product_data = self.ks_map_product_template_data_for_odoo(product_json_data, instance)
                            odoo_main_product = self.env['product.template'].ks_create_product_template(
                                main_product_data)
                        else:
                            main_product_data = self.ks_map_product_template_data_for_odoo(product_json_data, instance,
                                                                                           odoo_main_product)
                            odoo_main_product.write(main_product_data)
                        woo_layer_product = self.create_woo_product(instance, product_json_data, odoo_main_product)
                        if instance and instance.ks_want_maps:
                            if 'barcode_check_field' in main_product_data.keys():
                                product_barcode_exist = self.env['product.product'].search(
                                    [('barcode', '=', main_product_data.get('barcode_check_field'))])
                                main_product_data.pop('barcode_check_field', None)
                                if product_barcode_exist:
                                    _logger.error(f'Product barcode already exist for the product.')
                                    self.env.cr.commit()
                                    return False
                        if instance.ks_sync_price:
                            woo_layer_product.ks_product_template.product_variant_id.ks_manage_price_to_import(instance,
                                                                                                               product_json_data.get(
                                                                                                                   "regular_price"),
                                                                                                               product_json_data.get(
                                                                                                                   "sale_price"))
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(product_json_data,
                                                                                         woo_layer_product,
                                                                                         "ks_woo_product_id")
                        if instance.ks_sync_images:
                            self.env['ks.woo.product.images'].ks_update_images_for_odoo(product_json_data.get("images"),
                                                                                        product=woo_layer_product.id)

                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message="Product import create success",
                                                                           ks_status="success",
                                                                           ks_type="product",
                                                                           ks_record_id=woo_layer_product.id,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=product_json_data.get(
                                                                               "id", 0),
                                                                           ks_woo_instance=instance)
                        woo_layer_product.ks_sync_date = datetime.datetime.now()
                        woo_layer_product.ks_last_exported_date = woo_layer_product.ks_sync_date
                        woo_layer_product.sync_update()

                        return woo_layer_product

                    except Exception as e:
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message=str(e),
                                                                           ks_status="failed",
                                                                           ks_type="product",
                                                                           ks_record_id=0,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=product_json_data.get(
                                                                               "id", 0),
                                                                           ks_woo_instance=instance)

            elif product_json_data.get("type") == 'variable':
                # Handle variable product import here
                if product_exist:
                    # Run Update of variable product here
                    try:
                        if product_exist.ks_woo_product_type == product_json_data.get("type"):
                            if instance and instance.ks_want_maps:
                                all_woo_variations = self.env['ks.woo.product.variant'].ks_woo_get_all_product_variant(
                                    instance,
                                    product_json_data.get("id"),
                                    include=product_json_data.get(
                                        "variations"))
                                for each_var in all_woo_variations:
                                    product_barcode_exist = self.check_similar_barcode_for_variable_product(instance,
                                                                                                            each_var)
                                    if product_barcode_exist:
                                        same_prod_var_id = self.env['ks.woo.product.variant'].search(
                                            [('ks_wc_instance', '=', instance.id),
                                             ('ks_woo_variant_id', '=', each_var.get('id'))]).ks_product_variant
                                        if ((same_prod_var_id.id not in product_barcode_exist.ids) or (
                                                not product_barcode_exist.ks_product_variant)):
                                            _logger.error(
                                                f'Product barcode already exist for the product of woo id {product_json_data.get("id")}.')
                                            self.env.cr.commit()
                                            return False
                            main_product_data = self.ks_map_product_template_data_for_odoo(product_json_data, instance,
                                                                                           product_exist.ks_product_template)
                            self.env['product.template'].ks_update_product_template(product_exist,
                                                                                    main_product_data)
                            self.update_woo_product(instance, product_exist, product_json_data)
                            self.env['ks.woo.connector.instance'].ks_woo_update_the_response(product_json_data,
                                                                                             product_exist,
                                                                                             "ks_woo_product_id")
                            layer_variations = self.env['ks.woo.product.variant'].ks_manage_variations_import(instance,
                                                                                                              product_exist.ks_product_template,
                                                                                                              product_exist,
                                                                                                              product_json_data)
                            product_exist.ks_product_template.update({'weight': product_json_data.get('weight') or 0.0,
                                                                      "volume": float(
                                                                          product_json_data.get('dimensions').get(
                                                                              'length') or 0.0) * float(
                                                                          product_json_data.get('dimensions').get(
                                                                              'height') or 0.0) * float(
                                                                          product_json_data.get('dimensions').get(
                                                                              'width') or 0.0),
                                                                      })
                            if instance.ks_sync_images:
                                self.env['ks.woo.product.images'].ks_update_images_for_odoo(
                                    product_json_data.get("images"),
                                    product=product_exist.id)
                                self.env['ks.woo.product.images'].ks_manage_variant_images_for_odoo(
                                    product_json_data.get("variations"), instance,
                                    product_exist)
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                               ks_model='product.template',
                                                                               ks_layer_model='ks.woo.product.template',
                                                                               ks_message="Product import update success",
                                                                               ks_status="success",
                                                                               ks_type="product",
                                                                               ks_record_id=product_exist.id,
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_woo_id=product_json_data.get(
                                                                                   "id", 0),
                                                                               ks_woo_instance=instance)

                            product_exist.ks_sync_date = datetime.datetime.now()
                            product_exist.ks_last_exported_date = product_exist.ks_sync_date
                            product_exist.sync_update()

                            return product_exist
                        else:
                            if queue_record:
                                queue_record.ks_update_failed_state()
                            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                               ks_model='product.template',
                                                                               ks_layer_model='ks.woo.product.template',
                                                                               ks_message="Product Type Change, Please delete the odoo side product and perform fresh import",
                                                                               ks_status="failed",
                                                                               ks_type="product",
                                                                               ks_record_id=0,
                                                                               ks_operation_flow="woo_to_odoo",
                                                                               ks_woo_id=product_json_data.get(
                                                                                   "id", 0),
                                                                               ks_woo_instance=instance)

                    except Exception as e:
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message=str(e),
                                                                           ks_status="failed", ks_type="product",
                                                                           ks_record_id=0,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=product_json_data.get(
                                                                               "id", 0),
                                                                           ks_woo_instance=instance)
                        _logger.error('Product Update Operation Failed. ks_record_id = %s, ks_woo_id = %s. Message: %s',
                                      0, product_json_data.get("id", 0), str(e))

                else:
                    # Run Create of variable product here
                    try:
                        if instance and instance.ks_want_maps:
                            all_woo_variations = self.env['ks.woo.product.variant'].ks_woo_get_all_product_variant(
                                instance,
                                product_json_data.get("id"),
                                include=product_json_data.get(
                                    "variations"))
                            for each_var in all_woo_variations:
                                product_barcode_exist = self.check_similar_barcode_for_variable_product(instance,
                                                                                                        each_var)
                                if product_barcode_exist:
                                    _logger.error(f'Product barcode already exist for the product.')
                                    self.env.cr.commit()
                                    return False
                        if not odoo_main_product:
                            main_product_data = self.ks_map_product_template_data_for_odoo(product_json_data, instance)
                            odoo_main_product = self.env['product.template'].ks_create_product_template(
                                main_product_data)
                        else:
                            main_product_data = self.ks_map_product_template_data_for_odoo(product_json_data, instance,
                                                                                           odoo_main_product)
                            odoo_main_product.write(main_product_data)
                        woo_layer_product = self.create_woo_product(instance, product_json_data, odoo_main_product)
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(product_json_data,
                                                                                         woo_layer_product,
                                                                                         "ks_woo_product_id")
                        layer_variations = self.env['ks.woo.product.variant'].ks_manage_variations_import(instance,
                                                                                                          odoo_main_product,
                                                                                                          woo_layer_product,
                                                                                                          product_json_data)
                        if instance.ks_sync_images:
                            self.env['ks.woo.product.images'].ks_update_images_for_odoo(product_json_data.get("images"),
                                                                                        product=woo_layer_product.id)

                            self.env['ks.woo.product.images'].ks_manage_variant_images_for_odoo(
                                product_json_data.get("variations"), instance,
                                woo_layer_product)
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message="Product import create success",
                                                                           ks_status="success",
                                                                           ks_type="product",
                                                                           ks_record_id=woo_layer_product.id,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=product_json_data.get(
                                                                               "id", 0),
                                                                           ks_woo_instance=instance)

                        woo_layer_product.ks_sync_date = datetime.datetime.now()
                        woo_layer_product.ks_last_exported_date = woo_layer_product.ks_sync_date
                        woo_layer_product.sync_update()

                        return woo_layer_product

                    except Exception as e:
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message=str(e),
                                                                           ks_status="failed",
                                                                           ks_type="product",
                                                                           ks_record_id=0,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=product_json_data.get(
                                                                               "id", 0),
                                                                           ks_woo_instance=instance)
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                               ks_model='product.template',
                                                               ks_layer_model='ks.woo.product.template',
                                                               ks_message=str(e),
                                                               ks_status="failed",
                                                               ks_type="product",
                                                               ks_record_id=0,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=product_json_data.get(
                                                                   "id", 0),
                                                               ks_woo_instance=instance)
            raise e

    def check_similar_barcode_for_variable_product(self, instance, variant):
        if instance and instance.ks_want_maps:
            var_data = {}
            if variant.get("meta_data"):
                product_maps = instance.ks_meta_mapping_ids.search(
                    [('ks_wc_instance', '=', instance.id),
                     ('ks_active', '=', True),
                     ('ks_model_id.model', '=', 'product.product')
                     ])
                for map in product_maps:
                    odoo_field = map.ks_fields.name
                    json_key = map.ks_key
                    for meta_data in variant.get("meta_data"):
                        if meta_data.get("key", '') == json_key:
                            var_data.update({
                                odoo_field: meta_data.get("value", '')
                            })
                if 'barcode' in var_data.keys():
                    product_barcode_exist = self.env['product.product'].search(
                        [('barcode', '=', var_data.get('barcode'))])
                    return product_barcode_exist
        return False

    def ks_cron_for_stock_export_update(self, instance):
        ks_wc_instance = self.env['ks.woo.connector.instance'].browse(instance)
        woo_all_products = self.env['ks.woo.product.template'].search(
            [('ks_wc_instance', '=', ks_wc_instance.id), ('ks_woo_product_id', '!=', False)])
        self.env['ks.woo.queue.jobs'].ks_create_product_stock_record_in_queue(ks_wc_instance, records=woo_all_products)

    def ks_manage_woo_product_template_export(self, instance, queue_record=False, product_config=False):
        """
        :param instance: ks.woo.connector.instance()
        :param queue_record: Boolean trigger for queue job
        :return: json response after updation or creation
        """
        try:
            product_exported = self.ks_woo_product_id
            product_template = self.ks_product_template
            if product_exported:
                try:
                    if queue_record and queue_record.ks_model == 'stock':
                        data = self.ks_prepare_product_stock_data_to_export(product_config)
                    else:
                        data = self.ks_prepare_product_data_to_export(instance, product_template,
                                                                      self.ks_woo_product_type,
                                                                      product_config)
                    product_data_response = self.ks_woo_update_product(self.ks_woo_product_id, data, instance)
                    if product_data_response:
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(product_data_response, self,
                                                                                         'ks_woo_product_id', )
                        self.env['ks.woo.product.images'].ks_update_images_for_odoo(product_data_response.get("images"),
                                                                                    product=self.id)
                        self.ks_wc_variant_ids.filtered(
                            lambda x: x.ks_wc_instance.id == instance.id).ks_manage_woo_product_variant_export(instance,
                                                                                                               queue_record=queue_record,
                                                                                                               product_config=product_config)

                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_woo",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message="Product export update success",
                                                                           ks_status="success",
                                                                           ks_type="product",
                                                                           ks_record_id=self.ks_product_template.id,
                                                                           ks_operation_flow="odoo_to_woo",
                                                                           ks_woo_id=product_data_response.get("id", 0),
                                                                           ks_woo_instance=instance)
                        self.ks_sync_date = datetime.datetime.now()
                        self.ks_last_exported_date = self.ks_sync_date
                        self.sync_update()

                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                       ks_model='product.template',
                                                                       ks_layer_model='ks.woo.product.template',
                                                                       ks_message=str(e),
                                                                       ks_status="failed",
                                                                       ks_type="product",
                                                                       ks_record_id=self.ks_product_template.id,
                                                                       ks_operation_flow="odoo_to_woo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=instance)

            else:
                ##Use create command here
                try:
                    data = self.ks_prepare_product_data_to_export(instance, product_template, self.ks_woo_product_type,
                                                                  product_config)
                    product_data_response = self.ks_woo_post_product_template(data, instance)
                    if product_data_response:
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(product_data_response, self,
                                                                                         'ks_woo_product_id', )
                        self.env['ks.woo.product.images'].ks_update_images_for_odoo(product_data_response.get("images"),
                                                                                    product=self.id)
                        self.ks_wc_variant_ids.filtered(
                            lambda x: x.ks_wc_instance.id == instance.id).ks_manage_woo_product_variant_export(instance,
                                                                                                               product_config=product_config)

                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_woo",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message="Product export create success",
                                                                           ks_status="success",
                                                                           ks_type="product",
                                                                           ks_record_id=self.ks_product_template.id,
                                                                           ks_operation_flow="odoo_to_woo",
                                                                           ks_woo_id=product_data_response.get(
                                                                               "id", 0),
                                                                           ks_woo_instance=instance)
                        self.ks_sync_date = datetime.datetime.now()
                        self.ks_last_exported_date = self.ks_sync_date
                        self.sync_update()

                    else:
                        if queue_record:
                            queue_record.ks_update_failed_state()
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                           ks_model='product.template',
                                                                           ks_layer_model='ks.woo.product.template',
                                                                           ks_message="Product Export to woocommerce failed",
                                                                           ks_status="failed",
                                                                           ks_type="product",
                                                                           ks_record_id=self.ks_product_template.id,
                                                                           ks_operation_flow="odoo_to_woo",
                                                                           ks_woo_id=0,
                                                                           ks_woo_instance=instance)

                except Exception as e:
                    if queue_record:
                        queue_record.ks_update_failed_state()
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                       ks_model='product.template',
                                                                       ks_layer_model='ks.woo.product.template',
                                                                       ks_message=str(e),
                                                                       ks_status="failed",
                                                                       ks_type="product",
                                                                       ks_record_id=self.ks_product_template.id,
                                                                       ks_operation_flow="odoo_to_woo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=instance)
        except Exception as e:
            _logger.error(traceback.format_exc())
            if queue_record:
                queue_record.ks_update_failed_state()

            _logger.info(str(e))

    def ks_prepare_product_stock_data_to_export(self, product_config=False):
        server_action = product_config.get("server_action") == True if product_config else False
        data = {}
        if self.ks_woo_product_type == "simple":
            if self.ks_product_template.product_variant_id:
                variant = self.ks_product_template.product_variant_id
                stock_qty = self.env['product.product'].ks_get_stock_quantity(self.ks_wc_instance.ks_warehouse,
                                                                              variant,
                                                                              self.ks_wc_instance.ks_stock_field_type.name)
                data.update({
                    "manage_stock": True,
                    "stock_quantity": stock_qty,
                    "stock_status": "instock" if stock_qty > 0 else "outofstock",
                })
        return data

    def ks_prepare_product_data_to_export(self, instance, product_template, product_type=False, product_config=False,
                                          export_oper_type=False):
        """
        :param instance: ks.woo.connector.instance()
        :param product_template: product.template()
        :param product_type: simple / variable (optional)
        :return: woo compatible json data
        """
        server_action = product_config.get("server_action") == True if product_config else False
        data = {
            "name": product_template.name,
            "type": product_type,
        }
        if server_action:
            if product_config['basic_info'] == True:
                data.update({
                    "description": product_config['description'] or '',
                    "short_description": product_config['short_description'] or '',
                    "weight": str(product_template.weight) or "",
                    "dimensions":
                        {
                            "length": str(product_template.ks_length) or '',
                            "width": str(product_template.ks_width) or '',
                            "height": str(product_template.ks_height) or ''
                        },
                    "categories": [self.ks_manage_category_to_export(instance, product_template)],
                    "tags": self.ks_manage_tags_to_export(instance, self.ks_wc_tag_ids) if self.ks_wc_tag_ids else []
                })
            data.update({
                "status": "publish" if product_config["web_status"] == 'published' else "draft"
            })
        else:
            data.update({
                "status": "publish" if self.ks_published else "draft"
            })
        if self.ks_woo_product_type == "simple":
            if self.ks_product_template.product_variant_id:
                variant = self.ks_product_template.product_variant_id
                stock_qty = self.env['product.product'].ks_get_stock_quantity(self.ks_wc_instance.ks_warehouse,
                                                                              variant,
                                                                              self.ks_wc_instance.ks_stock_field_type.name)
                sale_price = self.ks_wc_instance.ks_woo_sale_pricelist.ks_get_product_price(variant, instance, self)
                if server_action:
                    if product_config["price"] == True:
                        data.update({
                            "regular_price": str(
                                self.ks_wc_instance.ks_woo_regular_pricelist.ks_get_product_price(variant, instance,
                                                                                                  self)),
                            "sale_price": str(sale_price) if sale_price else ''
                        })
                    if product_config['stock'] == True:
                        data.update({
                            "manage_stock": True,
                            "stock_quantity": stock_qty,
                            "stock_status": "instock" if stock_qty > 0 else "outofstock",
                            "sku": variant.default_code if variant.default_code else ''
                        })
                else:
                    data.update({
                        "manage_stock": True,
                        "stock_quantity": stock_qty,
                        "stock_status": "instock" if stock_qty > 0 else "outofstock",
                        "regular_price": str(
                            self.ks_wc_instance.ks_woo_regular_pricelist.ks_get_product_price(variant, instance, self)),
                        "sale_price": str(sale_price) if sale_price else '',
                        "sku": variant.default_code if variant.default_code else ''
                    })
        else:
            data.update({
                "manage_stock": False,
                "stock_status": "instock",
                "regular_price": '0',
                "sale_price": '0',
                "attributes": self.ks_manage_product_attributes(self.ks_product_template)
            })
        if self.ks_wc_image_ids:
            if server_action:
                if product_config["image"] == True:
                    data.update({"images": self.ks_wc_image_ids.ks_prepare_images_for_woo(layer_product=self)})
            else:
                data.update({"images": self.ks_wc_image_ids.ks_prepare_images_for_woo()})

        if instance and instance.ks_want_maps:
            if self.ks_woo_product_type == "simple":
                meta = {"meta_data": []}
                product_maps = instance.ks_meta_mapping_ids.search([('ks_wc_instance', '=', instance.id),
                                                                    ('ks_active', '=', True),
                                                                    ('ks_model_id.model', '=', 'product.template')
                                                                    ])
                for map in product_maps:
                    json_key = map.ks_key
                    odoo_field = map.ks_fields
                    query = """
                        select coalesce(%s, '') from product_product where id = %s
                    """ % (odoo_field.name, product_template.product_variant_id.id)
                    self.env.cr.execute(query)
                    results = self.env.cr.fetchall()
                    if results:
                        meta['meta_data'].append({
                            "key": json_key,
                            "value": str(results[0][0])
                        })
                        data.update(meta)
        return data

    def ks_manage_product_attributes(self, product_template):
        attribute_data = []
        attribute_line_ids = product_template.attribute_line_ids
        if attribute_line_ids:
            for line in attribute_line_ids:
                attribute_layer_exist = self.env['ks.woo.product.attribute'].check_if_already_prepared(
                    self.ks_wc_instance,
                    line.attribute_id)
                if attribute_layer_exist:
                    if not attribute_layer_exist.ks_woo_attribute_id:
                        attribute_layer_exist.create_woo_record(self.ks_wc_instance, line.attribute_id)
                    else:
                        attribute_layer_exist.update_woo_record(self.ks_wc_instance, line.attribute_id)
                    attribute_layer_exist.ks_manage_attribute_export()
                    data = {
                        "id": attribute_layer_exist.ks_woo_attribute_id,
                        "name": attribute_layer_exist.ks_name,
                        "variation": True
                    }
                    values = line.value_ids
                    if values:
                        term_data = values.mapped("name")
                        if term_data:
                            data.update({
                                "options": term_data
                            })
                else:
                    data = {
                        "id": 0,
                        "name": line.attribute_id.name,
                        "variation": True
                    }
                    term_data = line.value_ids.mapped("name")
                    if term_data:
                        data.update({
                            "options": term_data
                        })
                if data:
                    attribute_data.append(data)
        return attribute_data

    def ks_manage_tags_to_export(self, instance, layer_tags):
        """
        :param instance: ks.woo.connector.instance()
        :param layer_tags: ks.woo.product.tag()
        :return: json data for tag
        """
        data = []
        for tag in layer_tags:
            if tag.ks_woo_tag_id:
                tag_data = tag.ks_update_tag_odoo_to_woo()
            else:
                tag_data = tag.ks_create_tag_odoo_to_woo()

            data.append({'id': tag_data.get("id")})

        return data

    def ks_manage_category_to_export(self, instance, product_template):
        """
        :param instance: ks.woo.connector.instance()
        :param product_template: product.template()
        :return: json data for category
        """
        layer_category = product_template.categ_id.ks_product_category.filtered(
            lambda x: x.ks_wc_instance.id == instance.id)
        if not layer_category:
            layer_category = self.env['ks.woo.product.category'].create_woo_record(instance, product_template.categ_id)
        category_response = layer_category.ks_manage_category_export(product_template)
        data = {}
        if category_response:
            data = {
                "id": category_response.get("id")
            }
        return data

    def check_if_already_prepared(self, instance, odoo_product):
        """
        Checks if record is already prepared to be imported on layer model
        :param instance: woocommerce instance
        :param odoo_product: product.template()
        :return: product_category
        """
        odoo_product_exists = self.search([('ks_wc_instance', '=', instance.id),
                                           ('ks_product_template', '=', odoo_product.id)], limit=1)
        if odoo_product_exists:
            return odoo_product_exists
        else:
            return False

    def create_woo_record(self, instance, odoo_product, export_to_woo=False, queue_record=False, product_config=False):
        """
        :param instance: ks.woo.connector.instance()
        :param odoo_product: product.template()
        :param export_to_woo: optional, If want to directly export it or not
        :param queue_record: Boolean trigger for queue record
        :return: ks.woo.product.template()
        """
        try:
            layer_product = None
            product_exists = self.search([('ks_wc_instance', '=', instance.id),
                                          ('ks_product_template', '=', odoo_product.id)])
            if not product_exists:
                data = self.ks_map_prepare_data_for_layer(instance, odoo_product)
                layer_product = self.create(data)
                if layer_product.ks_woo_product_type == 'variable':
                    self.env['ks.woo.product.variant'].ks_manage_prepare_variant(odoo_product, layer_product, instance,
                                                                                 operation='create')
                else:
                    self.env['product.product'].ks_manage_price_to_export(
                        layer_product.ks_product_template.product_variant_id,
                        instance)
                self.env['product.template'].ks_manage_template_images(layer_product, odoo_product)

                if export_to_woo:
                    try:
                        layer_product.ks_manage_woo_product_template_export(instance=instance)
                    except Exception as e:
                        _logger.info(str(e))
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                   status="success",
                                                                   type="product",
                                                                   instance=instance,
                                                                   odoo_model="product.template",
                                                                   layer_model="ks.woo.product.template",
                                                                   id=odoo_product.id,
                                                                   message="Layer preparation Success")
            return layer_product
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()

            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                   status="failed",
                                                                   type="product",
                                                                   instance=instance,
                                                                   odoo_model="product.template",
                                                                   layer_model="ks.woo.product.template",
                                                                   id=odoo_product.id,
                                                                   message=str(e))

    def update_woo_record(self, instance, odoo_product, export_to_woo=False, queue_record=False, product_config=False):
        """
            :param instance: ks.woo.connector.instance()
            :param odoo_product: product.template()
            :param export_to_woo: optional, If want to directly export it or not
            :param queue_record: Boolean trigger for queue record
            :return: ks.woo.product.template()
        """
        try:
            product_exists = self.search([('ks_wc_instance', '=', instance.id),
                                          ('ks_product_template', '=', odoo_product.id)])
            if product_exists:
                data = self.ks_map_prepare_data_for_layer(instance, odoo_product)
                product_exists.write(data)
                if product_exists.ks_woo_product_type == 'variable':
                    self.env['ks.woo.product.variant'].ks_manage_prepare_variant(odoo_product, product_exists, instance,
                                                                                 operation='update')
                else:
                    self.env['product.product'].ks_manage_price_to_export(
                        product_exists.ks_product_template.product_variant_id,
                        instance)
                self.env['product.template'].ks_manage_template_images(product_exists, odoo_product)
                if export_to_woo:
                    try:
                        product_exists.ks_manage_woo_product_template_export(instance=instance)
                    except Exception as e:
                        _logger.info(str(e))
            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                   status="success",
                                                                   type="product",
                                                                   instance=instance,
                                                                   odoo_model="product.template",
                                                                   layer_model="ks.woo.product.template",
                                                                   id=odoo_product.id,
                                                                   message="Layer preparation Success")
            return product_exists

        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()

            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                   status="failed",
                                                                   type="product",
                                                                   instance=instance,
                                                                   odoo_model="product.template",
                                                                   layer_model="ks.woo.product.template",
                                                                   id=odoo_product.id,
                                                                   message=str(e))

    def ks_map_prepare_data_for_layer(self, instance, odoo_product, product_config=False):
        """
        :param instance: ks.woo.connector.instance()
        :param odoo_product: product.template
        :return: layer compatible json data
        """

        data = {
            "ks_product_template": odoo_product.id,
            "ks_wc_instance": instance.id,
            "ks_woo_product_type": 'simple' if odoo_product.product_variant_count == 1 else 'variable',
            "ks_company_id": instance.ks_company_id.id,
        }
        if product_config:
            if product_config.get('description'):
                data.update({
                    'ks_woo_description': product_config.get('description')
                })
            if product_config.get('short_description'):
                data.update({
                    'ks_woo_short_description': product_config.get('short_description')
                })
        return data

    def ks_map_product_template_data_for_layer(self, instance, product_json_data, odoo_main_product):
        layer_tags = []
        for tag in product_json_data.get("tags"):
            tag_json_data = self.env['ks.woo.product.tag'].ks_woo_get_product_tag(tag.get("id"), instance)
            tag_exist = self.env['ks.woo.product.tag'].search([
                ('ks_woo_tag_id', '=', tag.get("id", '')),
                ('ks_wc_instance', '=', instance.id)])
            if tag_exist:
                tag_exist.ks_woo_import_product_tag_update(tag_json_data, instance)
                layer_tags.append(tag_exist.id)
            else:
                layer_tag = self.env['ks.woo.product.tag'].ks_manage_woo_product_tag_import(instance, tag_json_data)
                layer_tags.append(layer_tag.id)
        data = {
            "ks_woo_product_type": product_json_data.get("type"),
            'ks_woo_product_id': product_json_data.get('id'),
            'ks_published': product_json_data.get('status') == 'publish',
            'ks_woo_description': product_json_data.get('description') or '',
            'ks_woo_short_description': product_json_data.get('short_description') or '',
            "ks_wc_instance": instance.id,
            "ks_product_template": odoo_main_product.id,
            "ks_company_id": instance.ks_company_id.id,

        }
        if layer_tags:
            data.update({"ks_wc_tag_ids": layer_tags})
        else:
            data.update({"ks_wc_tag_ids": False})
        return data

    def ks_map_product_template_data_for_odoo(self, json_data, instance, main_product=False):
        category_json_data = False
        if json_data.get("categories"):
            category_json_data = self.env['ks.woo.product.category'].ks_woo_get_category(
                json_data.get("categories")[0]["id"], instance)
        else:
            category_data = self.env['ks.woo.product.category'].search([('ks_slug', '=', 'uncategorized')],
                                                                       limit=1)
            category_json_data = self.env['ks.woo.product.category'].ks_woo_get_category(
                category_data.ks_woo_category_id, instance)
        data = {
            "name": json_data.get('name') or '',
            "company_id": instance.ks_company_id.id,
            "default_code": json_data.get('sku') or '',
            "type": "product",
            "weight": json_data.get('weight') or '',
            "ks_length": json_data.get('dimensions').get('length') or '',
            "ks_height": json_data.get('dimensions').get('height') or '',
            "ks_width": json_data.get('dimensions').get('width') or '',
            "volume": float(json_data.get('dimensions').get('length') or 0.0) * float(
                json_data.get('dimensions').get('height') or 0.0) * float(
                json_data.get('dimensions').get('width') or 0.0),
            "categ_id": self.env['ks.woo.product.category'].ks_manage_catgeory_import(instance,
                                                                                      category_json_data).id if category_json_data else False,
        }
        if json_data.get("type") == 'variable':
            ##Update data with attribute line ids
            attribute_json_data = json_data.get("attributes") if json_data.get("attributes") else []
            # FIX - 29/10/2021
            # Taking only those attributes whose variations = True i.e they have been "Used in Variations"
            attribute_json_data = [json_data for json_data in attribute_json_data if json_data.get("variation")]
            if attribute_json_data:
                odoo_attributes = self.ks_manage_attributes_import(instance, attribute_json_data, main_product)
                data.update({"attribute_line_ids": odoo_attributes})

        if instance and instance.ks_want_maps:
            if json_data.get("meta_data"):
                product_maps = instance.ks_meta_mapping_ids.search([('ks_wc_instance', '=', instance.id),
                                                                    ('ks_active', '=', True),
                                                                    ('ks_model_id.model', '=', 'product.template')
                                                                    ])
                for map in product_maps:
                    odoo_field = map.ks_fields.name
                    json_key = map.ks_key
                    for meta_data in json_data.get("meta_data"):
                        if meta_data.get("key", '') == json_key:
                            if odoo_field == 'barcode' and len(meta_data.get("value")) == 0 and json_data.get(
                                    "type") == 'simple':
                                meta_data.update({'value': False})
                                data.update({'barcode_check_field': ''})
                            elif odoo_field == 'barcode' and len(meta_data.get("value")) != 0 and json_data.get(
                                    "type") == 'simple':
                                data.update({'barcode_check_field': meta_data.get("value", '')})
                            data.update({
                                odoo_field: meta_data.get("value", '')
                            })

        return data

    def ks_manage_attributes_import(self, instance, attribute_json_data, main_product=False):
        """
        :param instance: ks.woo.connector.instance()
        :param attribute_json_data: attributes json data from woocommerce
        :return: odoo ids of attributes
        """
        attribute_line_data = []
        for attr in attribute_json_data:
            woo_attr_json = self.env['ks.woo.product.attribute'].ks_woo_get_attribute(attr.get("id"), instance)
            odoo_attribute = self.env['ks.woo.product.attribute'].ks_manage_attribute_import(instance,
                                                                                             woo_attr_json if woo_attr_json else attr)
            if main_product:
                attribute_exist = main_product.attribute_line_ids.search([('attribute_id', '=', odoo_attribute.id),
                                                                          ('product_tmpl_id', '=', main_product.id)],
                                                                         limit=1)
            else:
                attribute_exist = False
            value_ids = []
            if attr.get('options'):
                for att_terms in attr.get('options'):
                    att_value = self.env['product.attribute.value'].ks_manage_attribute_value_in_odoo(att_terms,
                                                                                                      odoo_attribute.id)
                    value_ids.append(att_value.id)
            if attribute_exist:
                attribute_line_data.append((1, attribute_exist.id, {
                    'attribute_id': odoo_attribute.id,
                    'product_tmpl_id': main_product.id,
                    'value_ids': [(6, 0, value_ids)]
                }))
            else:
                attribute_line_data.append((0, 0, {'attribute_id': odoo_attribute.id,
                                                   'value_ids': [(6, 0, value_ids)]}))

        return attribute_line_data

    def update_record_data_in_odoo(self):
        pass

    def ks_get_product_data_for_stock_adjustment(self, product_data, instance):
        if instance.ks_woo_auto_stock_import and type(product_data) != list:
            product_data = [product_data]
        product_json = []
        for product in product_data:
            if instance.ks_woo_auto_stock_import and type(product) != dict:
                product = json.loads(product)
            woo_product = self.search([('ks_woo_product_id', '=', product.get('id')),
                                       ('ks_wc_instance', '=', instance.id)], limit=1)
            if woo_product:
                variation_id = product.get('variations')
                if variation_id:
                    for each_variation in variation_id:
                        woo_product_variant = self.env['ks.woo.product.variant'].search(
                            [('ks_woo_variant_id', '=', each_variation),
                             ('ks_wc_instance', '=', instance.id)], limit=1)
                        if woo_product_variant:
                            woo_variant_record = self.ks_woo_get_product(each_variation, instance)
                            if woo_variant_record:
                                if woo_variant_record.get('manage_stock') and woo_variant_record.get(
                                        'manage_stock') != 'parent':
                                    if woo_variant_record.get('stock_quantity') != 0:
                                        product_json.append({
                                            'product_id': woo_product_variant.ks_product_variant.id,
                                            'product_qty': woo_variant_record.get('stock_quantity'),
                                        })
                if product.get('type') in ['simple'] and product.get('manage_stock'):
                    linked_product = woo_product.ks_product_template.product_variant_id
                    if product.get('stock_quantity') != 0:
                        product_json.append({
                            'product_id': linked_product.id,
                            'product_qty': product.get('stock_quantity'),
                        })
        return product_json

    def write(self, values):
        for rec in self:
            if rec.ks_woo_product_id:
                values.update({'ks_sync_date': datetime.datetime.now()})

        return super(KsWooProductTemplate, self).write(values)


class KsProductTemplateInherit(models.Model):
    _inherit = "product.template"

    ks_product_template = fields.One2many('ks.woo.product.template', 'ks_product_template')
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    ks_woo_product_id = fields.Integer(string='Woo Product Id', related='ks_product_template.ks_woo_product_id')

    def ks_get_odoo_products(self, instance, include=False, product_config=False, date_before=False, date_after=False):
        ks_include = include
        ks_include_split = ks_include.split(',')
        for rec in ks_include_split:
            product = self.search([]).filtered(lambda x: x.id == int(rec))
            if not product.ks_woo_product_id:
                layer_product = self.env['ks.woo.product.template'].create_woo_record(instance, product,
                                                                                      product_config=product_config)
            else:
                layer_product = self.env['ks.woo.product.template'].update_woo_record(instance, product,
                                                                                      product_config=product_config)
            if layer_product:
                self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(records=layer_product,
                                                                                product_config=product_config)
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def get_product_id(self, instance, product_config=False, date_before=False, date_after=False):
        product_list = []
        product_id = self.search([('create_date', '>=', date_after), ('create_date', '<=', date_before)])
        for product in product_id:
            if not product.ks_woo_product_id:
                layer_product = self.env['ks.woo.product.template'].create_woo_record(instance, product,
                                                                                      product_config=product_config)
            else:
                layer_product = self.env['ks.woo.product.template'].update_woo_record(instance, product,
                                                                                      product_config=product_config)
            product_list.append(layer_product)
        if layer_product:
            self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(records=product_list,
                                                                            product_config=product_config)
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_manage_product_category(self, woo_product, template):
        if template.categ_id:
            woo_category = self.env['ks.woo.product.category'].check_if_already_prepared(woo_product.ks_wc_instance,
                                                                                         template.categ_id)
            if not woo_category:
                woo_category = self.env['ks.woo.product.category'].create_woo_record(woo_product.ks_wc_instance,
                                                                                     template.categ_id,
                                                                                     export_to_woo=False)
            woo_product.ks_wc_category_ids = [(4, woo_category.id)]

    def ks_manage_product_variant(self, woo_product, product_template):
        for variant in product_template.product_variant_ids:
            product_attr_value_exist = self.env['ks.woo.product.variant'].check_if_already_prepared(
                woo_product.ks_wc_instance,
                variant)
            if product_attr_value_exist:
                self.env['ks.woo.product.variant'].update_woo_record(woo_product.ks_wc_instance, variant, woo_product)
            else:
                self.env['ks.woo.product.variant'].create_woo_record(woo_product.ks_wc_instance, variant, woo_product)

    def action_woo_layer_templates(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("ks_woocommerce.action_ks_woo_product_template_")
        action['domain'] = [('id', 'in', self.ks_product_template.ids)]
        return action

    def ks_manage_template_images(self, woo_product, template):
        if template.ks_image_ids:
            for image in template.ks_image_ids:
                image_id = self.env['ks.woo.product.images'].ks_odoo_prepare_image_data(image,
                                                                                        template_id=woo_product.id,
                                                                                        variant_id=False)
                if image.id == template.profile_image_id.id:
                    woo_product.profile_image = image_id.id

    def ks_push_to_woocommerce(self):
        action = self.env.ref("ks_woocommerce.s_action_ks_export_product_template").sudo().read()[0]
        return action

    def ks_pull_from_woocommerce(self):
        if self:
            instance_counts = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instance_counts) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_pull').sudo().read()[0]
                action['context'] = {'pull_from_woo': True}
                return action
            else:
                data_prepared = self.ks_product_template.filtered(lambda x: x.ks_wc_instance.id == instance_counts.id)
                if data_prepared and data_prepared.ks_woo_product_id:
                    ##Handle woo import hereself
                    woo_id = data_prepared.ks_woo_product_id
                    json_data = self.env['ks.woo.product.template'].ks_woo_get_product(woo_id, instance=instance_counts)
                    if json_data:
                        product = self.env['ks.woo.product.template'].ks_manage_woo_product_template_import(
                            instance_counts,
                            json_data)
                    else:
                        _logger.info("Fatal Error in Syncing Product from woocommerce")

                else:
                    _logger.info("Layer record must have woo id")
        else:
            active_ids = self.env.context.get("active_ids")
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_pull').sudo().read()[0]
                action['context'] = {'pull_from_woo': True, 'active_ids': active_ids,
                                     'active_model': 'product.template'}
                return action
            else:
                records = self.browse(active_ids)
                if len(records) == 1:
                    data_prepared = records.ks_product_template.filtered(lambda x: x.ks_wc_instance.id == instances.id)
                    if data_prepared and data_prepared.ks_woo_product_id:
                        woo_id = data_prepared.ks_woo_product_id
                        json_data = self.env['ks.woo.product.template'].ks_woo_get_product(woo_id,
                                                                                           instance=instances)
                        if json_data:
                            product = self.env['ks.woo.product.template'].ks_manage_woo_product_template_import(
                                instances,
                                json_data)
                        else:
                            _logger.info("Fatal Error in Syncing Product from woocommerce")

                    else:
                        _logger.info("Layer record must have woo id")

                else:
                    for rec in records:
                        data_prepared = rec.ks_product_template.filtered(
                            lambda x: x.ks_wc_instance.id == instances.id)
                        woo_id = data_prepared.ks_woo_product_id
                        if woo_id:
                            json_data = self.env['ks.woo.product.template'].ks_woo_get_product(woo_id,
                                                                                               instance=instances)
                            if json_data:
                                self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(instances, [json_data])
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_manage_direct_syncing(self, record, instance_ids, push=False, pull=False):
        try:
            for instance in instance_ids:
                if pull:
                    ##Handling of pull ther records from woocommerce here
                    data_prepared = record.ks_product_template.filtered(lambda x: x.ks_wc_instance.id == instance.id)
                    if data_prepared and data_prepared.ks_woo_product_id:
                        ##Handle woo import here
                        woo_id = data_prepared.ks_woo_product_id
                        json_data = self.env['ks.woo.product.template'].ks_woo_get_product(woo_id, instance=instance)
                        if json_data:
                            product = self.env['ks.woo.product.template'].ks_manage_woo_product_template_import(
                                instance, json_data)
                        else:
                            _logger.info("Fatal Error in Syncing Product from woocommerce")

                    else:
                        _logger.info("Layer record must have woo id")
        except Exception as e:
            _logger.info(str(e))

    def open_mapper(self):
        active_records = self._context.get("active_ids", False)
        model = self.env['ir.model'].search([('model', '=', self._name)])
        mapping_wizard = self.env['ks.global.record.mapping'].action_open_product_mapping_wizard(model, active_records,
                                                                                                 "Product Record Mapping")
        return mapping_wizard

    def write(self, values):
        for rec in self:
            ks_woo_product_temp = self.env['ks.woo.product.template'].search([('ks_product_template.id', '=', rec.id)])
            for each_prod in ks_woo_product_temp:
                if each_prod.ks_woo_product_id:
                    each_prod.update({'ks_sync_date': datetime.datetime.now()})

        return super(KsProductTemplateInherit, self).write(values)


class KsPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Woo Instance")

    def write(self, vals):
        res = super(KsPricelistItem, self).write(vals)
        layer_product = self.product_tmpl_id.ks_product_template.filtered(
            lambda x: x.ks_wc_instance.id == self.ks_wc_instance.id)
        layer_product.ks_sync_status = True

        return res

    @api.onchange('fixed_price')
    def compare_sale_and_regular_price_export(self):
        ks_wc_instance = self.ks_wc_instance.id
        if self.product_tmpl_id and self._origin.id:
            if not ks_wc_instance:
                raise ValidationError(_("Please Select WC Instance before changing the price"))
            if self.product_tmpl_id.product_variant_count == 1:
                ks_woo_prod_temp_id = self.product_tmpl_id.ks_product_template.filtered(
                    lambda x: x.ks_wc_instance.id == ks_wc_instance)
                if ks_woo_prod_temp_id:
                    sale_pricelist = self.pricelist_id.search(
                        [('ks_wc_instance', '=', ks_wc_instance),
                         ('id', '=', self.pricelist_id._origin.id)]).ks_wc_sale_pricelist
                    regular_pricelist = self.pricelist_id.search(
                        [('ks_wc_instance', '=', ks_wc_instance),
                         ('id', '=', self.pricelist_id._origin.id)]).ks_wc_regular_pricelist
                    if sale_pricelist and ks_woo_prod_temp_id.ks_woo_rp_pricelist.fixed_price <= self.fixed_price:
                        raise ValidationError(_('Sale Price must be less than Regular Price.'))
                    elif regular_pricelist and ks_woo_prod_temp_id.ks_woo_sp_pricelist.fixed_price >= self.fixed_price:
                        raise ValidationError(_('Regular Price must be greater than Sale Price.'))
                else:
                    raise ValidationError(_('Product does not exist for selected Instance'))

            elif self.product_tmpl_id.product_variant_count > 1:
                ks_woo_prod_var_id = self.product_id.ks_product_variant.filtered(
                    lambda x: x.ks_wc_instance.id == ks_wc_instance)
                if ks_woo_prod_var_id:
                    sale_pricelist = self.pricelist_id.search(
                        [('ks_wc_instance', '=', ks_wc_instance),
                         ('id', '=', self.pricelist_id._origin.id)]).ks_wc_sale_pricelist
                    regular_pricelist = self.pricelist_id.search(
                        [('ks_wc_instance', '=', ks_wc_instance),
                         ('id', '=', self.pricelist_id._origin.id)]).ks_wc_regular_pricelist
                    if sale_pricelist and ks_woo_prod_var_id.ks_woo_rp_pricelist.fixed_price <= self.fixed_price:
                        raise ValidationError(_('Sale Price must be less than Regular Price.'))
                    elif regular_pricelist and ks_woo_prod_var_id.ks_woo_sp_pricelist.fixed_price >= self.fixed_price:
                        raise ValidationError(_('Regular Price must be greater than Sale Price.'))
                else:
                    raise ValidationError(_('Product does not exist for selected Instance'))

    @api.onchange('ks_wc_instance')
    def validate_instance_product_for_pricelist(self):
        if self._origin.id:
            if not self.product_tmpl_id.ks_product_template.ks_wc_instance.id == self.ks_wc_instance.id:
                raise ValidationError(_('Instance is not associated with the existing product'))


class KSWooProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def ks_get_product_price(self, variant, instance, layer_template):
        """
        This function will return the product price from pricelist
        :param variant: product.product object
        :param instance: ks_woo_instance object
        :param partner: res_partner object
        :return:
        """
        final_price = 0.0
        if instance and variant:
            if layer_template:
                main_currency = instance.ks_woo_currency
                if main_currency.display_name == self.currency_id.display_name:
                    if layer_template.ks_woo_product_type == 'simple':
                        if self.ks_wc_sale_pricelist:
                            final_price = layer_template.ks_woo_sp_pricelist.fixed_price
                        elif self.ks_wc_regular_pricelist:
                            final_price = layer_template.ks_woo_rp_pricelist.fixed_price
                    else:
                        if self.ks_wc_sale_pricelist:
                            final_price = variant.ks_product_variant.ks_woo_sp_pricelist.fixed_price
                        elif self.ks_wc_regular_pricelist:
                            final_price = variant.ks_product_variant.ks_woo_rp_pricelist.fixed_price
            else:
                final_price = super(KSWooProductPricelist, self).ks_get_product_price(variant)
        return final_price


class InheritProductTemplate(models.Model):
    _inherit = "product.template"

    def link_image_to_gallery(self):
        self = self.search([('image_1920', '!=', False)])
        for res in self:
            image_values = {"sequence": 0,
                            "ks_image": res["image_1920"],
                            "ks_name": res.name,
                            "ks_template_id": res.id}
            image_id = self.env["ks.common.product.images"].with_context(main_image=True).create(image_values)
            res.profile_image_id = image_id.id


class InheritProduct(models.Model):
    _inherit = "product.product"

    def link_image_to_gallery(self):
        self = self.search([('image_1920', '!=', False)])
        for res in self:
            image_values = {"sequence": 0,
                            "ks_image": res["image_1920"],
                            "ks_name": res.name,
                            "ks_template_id": res.product_tmpl_id.id}
            image_id = self.env["ks.common.product.images"].with_context(main_image=True).create(image_values)
            res.profile_image_id = image_id.id
