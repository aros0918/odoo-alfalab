# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, ValidationError
from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)


class KsAutoProductSyncConfiguration(models.Model):
    _name = 'ks.woo.auto.product.syncing.configuration'
    _description = 'Woo Auto Product Syncing Configuration'

    name = fields.Char('Name', compute='ks_compute_name')
    ks_woo_instance_id = fields.Many2one("ks.woo.connector.instance", string="Woo Instance", ondelete='cascade',
                                         required=True)
    ks_product_auto_syncing = fields.Boolean(string="Product Auto Sync", default=False)
    ks_auto_sync_with = fields.Selection([('name', 'Product Name'), ('code', 'Product Code')], string="Sync With",
                                         default=False)

    # ks_woo_fields = fields.Selection([('sku', 'SKU')], string="Woo Field")
    ks_odoo_field = fields.Many2one('ir.model.fields', 'Odoo Field',
                                    domain="[('model_id', 'in', 'product.product')]")

    ks_company_id = fields.Many2one("res.company", string="Company", compute="_compute_company", store=True,
                                    help="Displays Company Name")

    @api.depends('ks_woo_instance_id')
    def _compute_company(self):
        """
        Computes company for the woo Auto Product Syncing Configuration
        :return:
        """
        for rec in self:
            if rec.ks_woo_instance_id.ks_company_id:
                rec.ks_company_id = rec.ks_woo_instance_id.ks_company_id.id
            else:
                rec.ks_company_id = self._context.get('company_id', self.env.company.id)

    def ks_compute_name(self):
        for rec in self:
            ks_name = "SKU" if rec.ks_auto_sync_with == 'code' else "Name"
            if ks_name and rec.ks_woo_instance_id.display_name:
                rec.name = rec.ks_woo_instance_id.display_name + ' ' + 'Auto Sync with' + ' ' + ks_name
            else:
                rec.name = False

    @api.constrains('ks_product_auto_syncing', 'ks_woo_instance_id')
    @api.onchange('ks_product_auto_syncing', 'ks_woo_instance_id')
    def ks_check_auto_conf_active(self):
        get_ids = self.env['ks.woo.auto.product.syncing.configuration'].search([('ks_product_auto_syncing', '=', True)])
        for rec in self:
            if rec.ks_woo_instance_id and rec.ks_product_auto_syncing:
                auto_sync_conf = get_ids.filtered(
                    lambda x: x.ks_woo_instance_id.id == rec.ks_woo_instance_id.id and x.id != rec.id)
                if len(auto_sync_conf) >= 1:
                    raise ValidationError(
                        _('To activate this configuration active, deselect the previously chosen configurations'
                          ' for instance %s.' % rec.ks_woo_instance_id.display_name))

    @api.constrains('ks_product_auto_syncing', 'ks_woo_instance_id')
    def ks_onchange_ks_product_auto_syncing(self):
        """
        Make The Cron Active and Deactivate
        """
        for rec in self:
            if rec.ks_woo_instance_id and rec.ids:
                get_ids = self.env['ks.woo.auto.product.syncing.configuration'].search(
                    [('ks_product_auto_syncing', '=', True), ('ks_woo_instance_id', '=', rec.ks_woo_instance_id.id),
                     ('id', '!=', rec.ids[0])])
                if rec.ks_woo_instance_id and rec.ks_product_auto_syncing:
                    rec.ks_woo_instance_id.ks_aps_cron_id.active = True
                elif not get_ids:
                    rec.ks_woo_instance_id.ks_aps_cron_id.active = False

    def ks_auto_product_syncing(self, cron_id=False):
        """
        Map the products which is exist on odoo and woo.
        :param cron_id:
        :return:
        """
        try:
            self = self.with_context(auto_sync_map=True)
            if not cron_id:
                if self._context.get('params'):
                    cron_id = self.env["ir.cron"].browse(self._context.get('params').get('id'))
            else:
                cron_id = self.env["ir.cron"].browse(cron_id)
            instance_id = cron_id.ks_wc_instance
            if instance_id and instance_id.ks_instance_state == 'active':
                all_product_data_from_woo = self.env['ks.woo.product.template'].ks_woo_get_all_products(
                    instance=instance_id)
                auto_sync_conf_rec = self.env['ks.woo.auto.product.syncing.configuration'].search(
                    [('ks_woo_instance_id', '=', instance_id.id),
                     ('ks_product_auto_syncing', '=', True)])
                not_sync_products = []
                already_sync_products = []
                if auto_sync_conf_rec and all_product_data_from_woo:
                    for product_json_data in all_product_data_from_woo:
                        woo_layer_product = self.env['ks.woo.product.template'].search(
                            [('ks_woo_product_id', '=', product_json_data.get('id')),
                             ('ks_wc_instance', '=', instance_id.id)])
                        if not woo_layer_product:
                            if product_json_data.get('type') == 'simple':
                                # variants = product_json_data.get('variations')[0]
                                woo_layer_product = self.ks_map_woo_product_to_odoo_product(instance_id,
                                                                                            auto_sync_conf_rec=auto_sync_conf_rec,
                                                                                            product_json_data=product_json_data)
                                if not woo_layer_product:
                                    not_sync_products.append(product_json_data.get('id'))
                            else:
                                woo_layer_product = False
                                variant_json = self.env['ks.woo.product.variant'].ks_woo_get_all_product_variant(
                                    instance_id, product_json_data.get("id"),
                                    include=product_json_data.get('variations'))
                                for variant in variant_json:
                                    woo_layer_product = self.ks_map_woo_product_to_odoo_product(instance_id,
                                                                                                auto_sync_conf_rec=auto_sync_conf_rec,
                                                                                                variants=variant,
                                                                                                product_json_data=product_json_data)
                                if not woo_layer_product:
                                    not_sync_products.append(product_json_data.get('id'))
                        else:
                            already_sync_products.append(product_json_data.get('id'))
                if already_sync_products:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="map_product",
                                                                       ks_model='product.template',
                                                                       ks_layer_model='ks.woo.product.template',
                                                                       ks_message="Products %s Already Sync." % already_sync_products,
                                                                       ks_status="failed",
                                                                       ks_type="product",
                                                                       ks_record_id=0,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=instance_id)
                if not_sync_products:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="map_product",
                                                                       ks_model='product.template',
                                                                       ks_layer_model='ks.woo.product.template',
                                                                       ks_message="Products %s incompatible/not found to Sync" % not_sync_products,
                                                                       ks_status="failed",
                                                                       ks_type="product",
                                                                       ks_record_id=0,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=instance_id)
        except Exception as e:
            _logger.info(str(e))
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="map_product",
                                                               ks_model='product.template',
                                                               ks_layer_model='ks.woo.product.template',
                                                               ks_message=str(e),
                                                               ks_status="failed",
                                                               ks_type="product",
                                                               ks_record_id=0,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=0,
                                                               ks_woo_instance=instance_id)

    def ks_map_woo_product_to_odoo_product(self, instance_id, auto_sync_conf_rec=False, variants=False,
                                           product_json_data=False):
        odoo_main_product = False
        woo_layer_product = False
        if auto_sync_conf_rec.ks_auto_sync_with == 'code':
            if variants and variants.get('sku'):
                odoo_product = self.env['product.product'].search([(
                    'default_code',
                    '=', variants.get('sku'))], limit=1)
                odoo_main_product = odoo_product.product_tmpl_id
            else:
                odoo_product = self.env['product.product'].search([(
                    'default_code',
                    '=', product_json_data.get('sku'))], limit=1)
                odoo_main_product = odoo_product.product_tmpl_id
        elif auto_sync_conf_rec.ks_auto_sync_with == 'name':
            odoo_main_product = self.env['product.template'].search([('name', '=', product_json_data.get('name'))],
                                                                    limit=1)
        if odoo_main_product:
            woo_layer_product = self.env['ks.woo.product.template'].ks_manage_woo_product_template_import(
                instance=instance_id, product_json_data=product_json_data,
                odoo_main_product=odoo_main_product)

            if woo_layer_product:
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="map_product",
                                                                   ks_model='product.template',
                                                                   ks_layer_model='ks.woo.product.template',
                                                                   ks_message="Product auto sync success",
                                                                   ks_status="success",
                                                                   ks_type="product",
                                                                   ks_record_id=woo_layer_product.id,
                                                                   ks_operation_flow="woo_to_odoo",
                                                                   ks_woo_id=product_json_data.get(
                                                                       "id", 0),
                                                                   ks_woo_instance=instance_id)
        return woo_layer_product
