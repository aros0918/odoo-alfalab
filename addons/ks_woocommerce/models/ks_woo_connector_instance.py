# -*- coding: utf-8 -*-

import base64
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from requests.exceptions import ConnectionError
from woocommerce import API as WC_API

_logger = logging.getLogger(__name__)


class KsWooCommerceConnectorInstance(models.Model):
    _name = "ks.woo.connector.instance"
    _rec_name = 'ks_instance_name'
    _description = "WooCommerce Connector Instance"

    def _get_default_language(self):
        super_user_lang = self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', super_user_lang)]).id
        return lang
    ks_instance_name = fields.Char(string='Connector Instance  Name ', required=True, translate=True, help="Displays WooCommerce Instance Name")
    ks_wc_instance = fields.Char(string='Connector Instance Name', related="ks_instance_name", store=True,
                                 translate=True)
    ks_instance_state = fields.Selection([('draft', 'Draft'), ('connected', 'Connected'), ('active', 'Active'),
                                          ('deactivate', 'Deactivate')], string="Instance State", default="draft")
    ks_company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,
                                    required=True, readonly=True, help=" Shows the name of the company")
    ks_instance_connected = fields.Boolean(default=False, string="Instance Connected")

    ks_store_url = fields.Char('Store URL', required=True, help="Displays the WooCommerce Store URL")
    ks_customer_key = fields.Char('Customer Key', required=True, help="Customer Key of the WooCommerce, not visible by default")
    ks_customer_secret = fields.Char('Customer Secret', required=True, help="Customer Secret of the WooCommerce, not visible by default")
    ks_verify_ssl = fields.Boolean('Verify SSL', help="Checkbox indicator for SSL Verification")
    ks_auth = fields.Boolean('Authorization', help="Checkbox indicator for Authorization")
    ks_version = fields.Selection([('wc/v3', '3.5.x or later'), ('wc/v2', '3.0.x or later'),
                                   ('wc/v1', '2.6.x or later')],
                                  string='WooCommerce Version', default='wc/v3', readonly=True,
                                  required=True, help="It displays the WooCommerce version being used")
    sequence = fields.Integer(string='Sequence', default=10)

    ks_warehouse = fields.Many2one('stock.warehouse', 'Warehouse', domain="[('company_id', '=', ks_company_id)]",
                                   help=_("Shows the location of the warehouse"))
    # ks_language = fields.Many2one('res.lang', string='Language', required=True, default=lambda self: self._get_default_language(), help=_("Select language for your Woo Instance"))

    ks_sync_images = fields.Boolean('Woo Sync/Import Images?', help=_("If checked, it will automatically Import Product"
                                                                      "image while import product process, else not"))
    ks_sync_price = fields.Boolean('Woo Sync/Import Price?',
                                   help=_("If checked, it will configure the Pricelist and set"
                                          " price into it for the Instance, else not."))
    ks_update_mapped_category = fields.Boolean('Woo Import/Update Category Name?', default=True,
                                               help=_("If checked, update the mapped categories also when product imported"))
    ks_sync_unpublished_product = fields.Boolean('Import Including Draft product?',
                                   help=_("If checked, it will import all product"
                                          " else product which not unpublished"))
    ks_weight_unit = fields.Many2one(
        'uom.uom', 'Unit of Measure')
    ks_woo_currency = fields.Many2one('res.currency', 'Main Currency', help="Shows the main currency in use")
    ks_order_date_after = fields.Datetime('Date After',
                                          help=_("The date after which the order records will be imported"))
    ks_order_date_before = fields.Datetime('Date Before',
                                           help=_("The date before which the order records will be imported"))
    ks_customer_company_type = fields.Boolean(string='Import Customer With Company Type', default=False)
    ks_multi_currency_option = fields.Boolean(string='Multi-Currency Option', default=False, help="Checkbox indicator for multi-currency feature")
    ks_woo_multi_currency = fields.Many2many(comodel_name='res.currency', string='Multi-Currency', help="Shows the other currencies selected")
    ks_woo_pricelist_ids = fields.Many2many('product.pricelist', string='Multi-Pricelist', readonly=True)
    ks_woo_regular_pricelist = fields.Many2one('product.pricelist', string='Regular Main Pricelist', readonly=True, help=" Manages regular sale price of the product from WooCommerce instance.")
    ks_woo_sale_pricelist = fields.Many2one('product.pricelist', string='OnSale Main Pricelist', readonly=True, help="Manages on sale price/discounted price of the product from WooCommerce instance.")
    ks_payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', help="Shows the payment term/mechanism")
    ks_custom_order_prefix = fields.Char(string="Order Prefix", default='WC', help="Prefix added on orders imported from woo to odoo is shown here")
    ks_default_order_prefix = fields.Boolean(string="Default Order Prefix", help="Enables/disables - default order prefix of the Odoo")
    ks_auto_order_status_update_to_woo = fields.Boolean(string="Auto Order Status Update to Woo", help="Enables/disables - automatically order status synchronisation with WooCommerce")
    ks_auto_order_date_update_to_created_date = fields.Boolean(string="Update Order/Quotation Date", help="Enables/disables - automatically Update Order/Quotation Date as created date")
    ks_auto_stock_sync_to_woo = fields.Boolean(string="Auto Stock Update to Woo", help="Enables/disables - automatically stock synchronisation with WooCommerce")
    ks_sales_team = fields.Many2one('crm.team', string="Sales Team", help="Shows the location of the sales team")
    ks_sales_person = fields.Many2one('res.users', string="Sales Person", help="Displays the name of the sales person")
    ks_invoice_tax_account = fields.Many2one('account.account', string="Invoice TAX Account", help="Show the tax account which will be used for invoice tax default account", domain="[('deprecated', '=', False), ('account_type', 'not in', ('receivable', 'payable')), ('company_id', '=', ks_company_id), ('is_off_balance', '=', False)]")
    ks_credit_tax_account = fields.Many2one('account.account', string="Credit Note TAX Account", help="Show the tax account which will be used for Credit Note/Refund tax default account", domain="[('deprecated', '=', False), ('account_type', 'not in', ('receivable', 'payable')), ('company_id', '=', ks_company_id), ('is_off_balance', '=', False)]")
    ks_stock_field_type = fields.Many2one('ir.model.fields', 'Stock Field Type',
                                          domain="[('model_id', '=', 'product.product'),"
                                                 "('name', 'in', ['free_qty','virtual_available'])]",
                                          help="Choose the field by which you want to update the stock in WooCommerce "
                                               "based on Free To Use(Quantity On Hand - Outgoing + Incoming) or "
                                               "Forecasted Quantity (Quantity On Hand - Reserved quantity).")
    ks_dashboard_id = fields.Many2one("ks.woo.dashboard", string="Dashboards")
    ks_sale_workflow_ids = fields.One2many('ks.woo.auto.sale.workflow.configuration', 'ks_wc_instance',
                                           string="Sale Workflow IDs", help="Shows the flow of the order when imported to the odoo")
    ks_order_status = fields.Many2many("ks.woo.order.status", string="Order Status", help="Shows the configuration of the imported order status")
    ks_order_import_type = fields.Selection([('status', 'Status'),
                                             ('payment_gateway', 'Payment Gateway')], default="status",
                                            string="Import Orders through", help="Shows the status of orders imported portal")
    ks_webhook_conf = fields.One2many("ks.webhooks.configuration", "ks_instance_id", string="Webhooks", help="Shows all the webhooks which are configured")
    ks_want_maps = fields.Boolean(string="Require Meta Mapping ?", help="If you turn this on, you can initiate the excellent meta mapping feature")
    ks_meta_mapping_ids = fields.One2many("ks.woo.meta.mapping", "ks_wc_instance", string="Meta Mappings")
    ks_email_ids = fields.One2many("email.entry", "ks_wc_instance", string="Emails", help="Sends a monthly sales report to the email-ids provided in it.")
    ks_orders_count = fields.Integer(compute="ks_woo_count", string="Orders Count")
    ks_products_count = fields.Integer(compute="ks_woo_count", string="Products Count")
    ks_customers_count = fields.Integer(compute="ks_woo_count", string="Customers Count")
    ks_coupons_count = fields.Integer(compute="ks_woo_count", string="Coupons Count")
    ks_import_customer_images = fields.Boolean(string="Import Customer Images", help="Enables/disables you to import the customer images along with customer data")
    # Auto Job Crons:
    ks_aip_cron_id = fields.Many2one('ir.cron', readonly=1, string="AIP Cron")
    ks_aio_cron_id = fields.Many2one('ir.cron', readonly=1, string = "AIO Cron")
    ks_auos_cron_id = fields.Many2one('ir.cron', readonly=1, string = "AUOS Cron")
    ks_aus_cron_id = fields.Many2one('ir.cron', readonly=1, string = "AUS Cron")
    ks_aeps_cron_id = fields.Many2one('ir.cron', readonly=1, string = "AEPS Cron")
    ks_aps_cron_id = fields.Many2one('ir.cron', readonly=1, string="Product Auto Sync Cron")
    ks_acs_cron_id = fields.Many2one('ir.cron', readonly=1, string="Customer Auto Sync Cron")
    ks_aep_cron_id = fields.Many2one('ir.cron', readonly=1, string="Auto Export Of New Products")
    ks_ausp_cron_id = fields.Many2one('ir.cron', readonly=1, string="Auto Update of Synced Products")
    ks_uwsw_cron_id = fields.Many2one('ir.cron', readonly=1, string = "Update Woo Saleorder Workflow Cron")
    ks_customer_address = fields.Selection([('billing', 'Billing Address'),
                                             ('shipping', 'Shipping Address')], default="billing",
                                            string="Customer Address",
                                            help="Shows the main address of customer.", required=True)
    ks_is_named_guest_customer = fields.Boolean('Actual/Guest customer', help="Enables/disables - Creation of Actual customer out Order's Guest Customer")
    ks_export_image_variation = fields.Boolean(string='Export Variation Images', help="Enables/disables - Variable profile image to be exported with product")
    ks_location_id = fields.Many2one('stock.location', 'Physical Location',
                                     domain="[('company_id', '=', ks_company_id),('usage','=','internal')]"
                                     )
    ks_automatic_reverse_workflow = fields.Boolean('Auto Reverse Workflow', help="Enables/disables - Reverse Worlflow will work automatically together with the Sale Workflow")
    ks_woo_auto_stock_import = fields.Boolean('Auto Product Stock Import')

    @api.onchange('ks_woo_auto_stock_import', 'ks_auto_stock_sync_to_woo')
    def ks_manage_import_export_stock(self):
        if self.ks_woo_auto_stock_import:
            if self.ks_auto_stock_sync_to_woo:
                raise ValidationError("Your  Stock Related one button already enable,You cannot enable this button "
                                      "right now,if you want to enable this button then first disable that  button !!")
        elif self.ks_auto_stock_sync_to_woo:
            if self.ks_woo_auto_stock_import:
                raise ValidationError("Your Stock Related one button already enable,You cannot enable this button"
                                      "right now,if you want to enable this button then first disable that  button "
                                      "!!!!")

    def ks_manage_priclists(self):
        # Manages all the price lists
        self.ensure_one()
        pricelists = self.env['product.pricelist']
        if self.ks_woo_currency:
            main_regular_price_list, main_sale_price_list = self.ks_check_for_pricelists(self.ks_woo_currency)
            self.ks_woo_regular_pricelist = main_regular_price_list
            pricelists += main_regular_price_list
            self.ks_woo_sale_pricelist = main_sale_price_list
            pricelists += main_sale_price_list
        for currency in self.ks_woo_multi_currency:
            main_regular_price_list, main_sale_price_list = self.ks_check_for_pricelists(currency)
            pricelists += main_regular_price_list
            pricelists += main_sale_price_list
        self.ks_woo_pricelist_ids = [(6, 0, pricelists.ids)]

    def ks_check_for_pricelists(self, currency):

        """
        Check if pricelist is available or not
        :param currency: currency model many2one domain
        :return: pricelists domain regular and sale
        """
        self.ensure_one()
        regular_price_list = self.env['product.pricelist'].search([('ks_wc_instance', '=', self.id),
                                                                   ('ks_wc_regular_pricelist', '=', True),
                                                                   ('currency_id', '=', currency.id)])
        sale_price_list = self.env['product.pricelist'].search([('ks_wc_instance', '=', self.id),
                                                                ('ks_wc_sale_pricelist', '=', True),
                                                                ('currency_id', '=', currency.id)])
        if not regular_price_list:
            regular_price_list = self.env['product.pricelist'].create({
                'name': '[ ' + self.ks_instance_name + ' ] ' + currency.name + ' Regular Pricelist',
                'currency_id': currency.id,
                'company_id': self.ks_company_id.id,
                'ks_wc_instance': self.id,
                'ks_wc_regular_pricelist': True
            })
        if not sale_price_list:
            sale_price_list = self.env['product.pricelist'].create({
                'name': '[ ' + self.ks_instance_name + ' ] ' + currency.name + ' Sale Pricelist',
                'currency_id': currency.id,
                'company_id': self.ks_company_id.id,
                'ks_wc_instance': self.id,
                'ks_wc_sale_pricelist': True
            })
        return regular_price_list, sale_price_list

    def ks_woo_count(self):
        # Counts the orders, products, customers, coupons for particular instance
        for rec in self:
            domain = [('ks_wc_instance', '=', rec.id)]
            rec.ks_orders_count = rec.env['sale.order'].search_count(domain)
            rec.ks_products_count = rec.env['ks.woo.product.template'].search_count(domain)
            rec.ks_customers_count = rec.env['ks.woo.partner'].search_count(domain)
            rec.ks_coupons_count = rec.env['ks.woo.coupons'].search_count(domain)

    @api.model_create_multi
    def create(self, values_list):

        """
        creates one time usable dashboard kanban
        :param values: create method vals
        :return: current domain
        """
        for values in values_list:
            values.update({
                'ks_dashboard_id': self.env.ref("ks_woocommerce.ks_woo_dashboard_1").id
            })
            res = super(KsWooCommerceConnectorInstance, self).create(values)
            # manage the Cron jobs
            res.ks_manage_auto_job()
            if values.get('ks_woo_multi_currency') or values.get('ks_woo_currency'):
                # manage the price lists according to the currency selected
                res.ks_manage_priclists()
        return res

    def write(self, values):
        # Write method overwritten
        res = super(KsWooCommerceConnectorInstance, self).write(values)
        # manage the Cron jobs
        self.ks_manage_auto_job()
        if values.get('ks_woo_multi_currency') or values.get('ks_woo_currency'):
            # manage the price lists according to the currency selected
            self.ks_manage_priclists()
        return res

    def ks_compute_base_url(self, operations):
        """
        Computes URL for controllers webhook to request data
        :return:
        """
        ks_base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        ks_base_updated = ks_base.split("//")
        if len(ks_base_updated) > 1:
            ks_base = 'https://' + ks_base_updated[1]
        selection_list = operations.split('_')
        base_url = '%s/woo_hook/%s/%s/%s/%s/%s' % (ks_base,
                                                       base64.urlsafe_b64encode(
                                                           self.env.cr.dbname.encode("utf-8")).decode(
                                                           "utf-8"),
                                                    str(self.env.user.id),
                                                       self.id,
                                                       selection_list[0],
                                                       selection_list[1])
        return base_url

    def ks_manage_webhooks(self):
        """
        Manages the webhook on the Odoo side
        :return: None
        """
        try:
            # Order Create Webhook
            base_url = self.ks_compute_base_url('order_create')
            # data = self.ks_woocommerce_webhook_data("order_create", base_url)
            # response_data = self.env['ks.webhooks.configuration'].ks_create_webhook(self, data)
            vals = self.ks_odoo_webhook_data('order_create', base_url)
            self.env['ks.webhooks.configuration'].create(vals)

            # Order Update Webhook
            base_url = self.ks_compute_base_url('order_update')
            # data = self.ks_woocommerce_webhook_data("order_update", base_url)
            # response_data = self.env['ks.webhooks.configuration'].ks_create_webhook(self, data)
            vals = self.ks_odoo_webhook_data('order_update', base_url)
            self.env['ks.webhooks.configuration'].create(vals)

            # Product Create Webhook
            base_url = self.ks_compute_base_url('product_create')
            # data = self.ks_woocommerce_webhook_data("product_create", base_url)
            # response_data = self.env['ks.webhooks.configuration'].ks_create_webhook(self, data)
            vals = self.ks_odoo_webhook_data('product_create', base_url)
            self.env['ks.webhooks.configuration'].create(vals)

            # Product Update Webhook
            base_url = self.ks_compute_base_url('product_update')
            # data = self.ks_woocommerce_webhook_data("product_update", base_url)
            # response_data = self.env['ks.webhooks.configuration'].ks_create_webhook(self, data)
            vals = self.ks_odoo_webhook_data('product_update', base_url)
            self.env['ks.webhooks.configuration'].create(vals)

            # Customer Create Webhook
            base_url = self.ks_compute_base_url('customer_create')
            # data = self.ks_woocommerce_webhook_data("customer_create", base_url)
            # response_data = self.env['ks.webhooks.configuration'].ks_create_webhook(self, data)
            vals = self.ks_odoo_webhook_data('customer_create', base_url)
            self.env['ks.webhooks.configuration'].create(vals)

            # Customer Update Webhook
            base_url = self.ks_compute_base_url('customer_update')
            # data = self.ks_woocommerce_webhook_data("customer_update", base_url)
            # response_data = self.env['ks.webhooks.configuration'].ks_create_webhook(self, data)
            vals = self.ks_odoo_webhook_data('customer_update', base_url)
            self.env['ks.webhooks.configuration'].create(vals)

            # Coupon Create Webhook
            base_url = self.ks_compute_base_url('coupon_create')
            # data = self.ks_woocommerce_webhook_data("coupon_create", base_url)
            # response_data = self.env['ks.webhooks.configuration'].ks_create_webhook(self, data)
            vals = self.ks_odoo_webhook_data('coupon_create', base_url)
            self.env['ks.webhooks.configuration'].create(vals)

            # Coupon Update Webhook
            base_url = self.ks_compute_base_url('coupon_update')
            # data = self.ks_woocommerce_webhook_data("coupon_update", base_url)
            # response_data = self.env['ks.webhooks.configuration'].ks_create_webhook(self, data)
            vals = self.ks_odoo_webhook_data('coupon_update', base_url)
            self.env['ks.webhooks.configuration'].create(vals)
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="webhook",
                                                               instance=self,
                                                               operation_flow="woo_to_odoo",
                                                               layer_model="ks.webhooks.configuration",
                                                               woo_id=0,
                                                               message=str(e))

        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="webhook",
                                                               operation_flow="woo_to_odoo",
                                                               instance=self,
                                                               layer_model="ks.webhooks.configuration",
                                                               woo_id=0,
                                                               message="Fetch of Webhooks successful")

    def ks_odoo_webhook_data(self, name, base_url):
        """
        Creates dictionary data for the odoo side
        :param name: Name of the Webhook
        :param base_url: Base URL of the webhook
        :return: Dictionary
        """
        return {
            'name': " ".join(name.split("_")).title(),
            'operations': name,
            'status': 'disabled',
            'ks_instance_id': self.id,
            'base_url': base_url,
            # 'ks_woo_id': response_data.get('id')
        }

    def ks_manage_auto_job(self):
        if not self.ks_aio_cron_id:
            auto_import_order_values = {
                'name': '[' + str(
                    self.id) + '] - ' + self.ks_instance_name + ': ' + 'WooCommerce Auto Order Import from Woo to Odoo (Do Not Delete)',
                'interval_number': 1,
                'interval_type': 'days',
                'user_id': self.env.user.id,
                'model_id': self.env.ref('sale.model_sale_order').id,
                'state': 'code',
                'active': False,
                'numbercall': -1,
                'ks_wc_instance': self.id,
            }
            self.ks_aio_cron_id = self.env['ir.cron'].create(auto_import_order_values)
            self.ks_aio_cron_id.code = 'model.ks_auto_import_wc_order(' + str(self.ks_aio_cron_id.id) + ')'
        if not self.ks_aeps_cron_id:
            auto_export_product_stock_values = {
                'name': '[' + str(
                    self.id) + '] - ' + self.ks_instance_name + ': ' + 'WooCommerce Auto Product Stock Export from Odoo to Woo',
                'interval_number': 1,
                'interval_type': 'days',
                'user_id': self.env.user.id,
                'model_id': self.env.ref('ks_woocommerce.model_ks_woo_product_template').id,
                'state': 'code',
                'active': False,
                'numbercall': -1,
                'ks_wc_instance': self.id,
            }
            self.ks_aeps_cron_id = self.env['ir.cron'].create(auto_export_product_stock_values)
            self.ks_aeps_cron_id.code = 'model.ks_cron_for_stock_export_update(' + str(self.id) + ')'
        if not self.ks_uwsw_cron_id:
            auto_update_woo_status = {
                'name': '[' + str(
                    self.id) + '] - ' + self.ks_instance_name + ': ' + 'Update Odoo Order Status Workflow (Do Not Delete)',
                'interval_number': 1,
                'interval_type': 'days',
                'user_id': self.env.user.id,
                'model_id': self.env.ref('ks_woocommerce.model_ks_woo_reverse_workflow_configuration').id,
                'state': 'code',
                'active': False,
                'numbercall': -1,
                'ks_wc_instance': self.id,
            }
            self.ks_uwsw_cron_id = self.env['ir.cron'].create(auto_update_woo_status)
            self.ks_uwsw_cron_id.code = 'model.ks_auto_update_woo_status(' + str(self.id) + ')'
        if not self.ks_auos_cron_id:
            auto_update_order_status = {
                'name': '[' + str(
                    self.id) + '] - ' + self.ks_instance_name + ': ' + 'WooCommerce Auto Order Status Update from Odoo to Woo(Do Not Delete)',
                'interval_number': 1,
                'interval_type': 'days',
                'user_id': self.env.user.id,
                'model_id': self.env.ref('sale.model_sale_order').id,
                'state': 'code',
                'active': False,
                'numbercall': -1,
                'ks_wc_instance': self.id,
            }
            self.ks_auos_cron_id = self.env['ir.cron'].create(auto_update_order_status)
            self.ks_auos_cron_id.code = 'model.ks_auto_update_wc_order_status(' + str(self.ks_auos_cron_id.id) + ')'
        if not self.ks_aps_cron_id:
            auto_product_sync_values = {
                'name': '[' + str(
                    self.id) + '] - ' + self.ks_instance_name + ': ' + 'Woo Auto Product Mapping from woo to Odoo (Do Not Delete)',
                'interval_number': 1,
                'interval_type': 'days',
                'user_id': self.env.user.id,
                'model_id': self.env.ref('ks_woocommerce.model_ks_woo_auto_product_syncing_configuration').id,
                'state': 'code',
                'active': False,
                'numbercall': -1,
                'ks_wc_instance': self.id,
            }
            self.ks_aps_cron_id = self.sudo().env['ir.cron'].create(auto_product_sync_values)
            self.sudo().ks_aps_cron_id.code = 'model.ks_auto_product_syncing(' + str(self.ks_aps_cron_id.id) + ')'
        if not self.ks_acs_cron_id:
            auto_customer_sync_values = {
                'name': '[' + str(
                    self.id) + '] - ' + self.ks_instance_name + ': ' + 'Woo Auto Customer Mapping from woo to Odoo (Do Not Delete)',
                'interval_number': 1,
                'interval_type': 'days',
                'user_id': self.env.user.id,
                'model_id': self.env.ref('ks_woocommerce.model_ks_woo_auto_customer_syncing_configuration').id,
                'state': 'code',
                'active': False,
                'numbercall': -1,
                'ks_wc_instance': self.id,
            }
            self.ks_acs_cron_id = self.sudo().env['ir.cron'].create(auto_customer_sync_values)
            self.sudo().ks_acs_cron_id.code = 'model.ks_auto_customer_syncing(' + str(self.ks_acs_cron_id.id) + ')'
        if not self.ks_aep_cron_id:
            auto_export_product = {
                'name': '[' + str(
                    self.id) + '] - ' + self.ks_instance_name + ': ' + 'WooCommerce Auto Export New Product from Odoo to Woo(Do Not Delete)',
                'interval_number': 1,
                'interval_type': 'days',
                'user_id': self.env.user.id,
                'model_id': self.env.ref('ks_woocommerce.model_ks_woo_product_template').id,
                'state': 'code',
                'active': False,
                'numbercall': -1,
                'ks_wc_instance': self.id,
            }
            self.ks_aep_cron_id = self.env['ir.cron'].create(auto_export_product)
            self.ks_aep_cron_id.code = 'model.ks_auto_export_wc_product(' + str(self.id) + ')'
        if not self.ks_ausp_cron_id:
            auto_update_product = {
                'name': '[' + str(
                    self.id) + '] - ' + self.ks_instance_name + ': ' + 'WooCommerce Auto Update Synced Product from Odoo to Woo(Do Not Delete)',
                'interval_number': 1,
                'interval_type': 'days',
                'user_id': self.env.user.id,
                'model_id': self.env.ref('ks_woocommerce.model_ks_woo_product_template').id,
                'state': 'code',
                'active': False,
                'numbercall': -1,
                'ks_wc_instance': self.id,
            }
            self.ks_ausp_cron_id = self.env['ir.cron'].create(auto_update_product)
            self.ks_ausp_cron_id.code = 'model.ks_auto_update_wc_product(' + str(self.id) + ')'

    def get_all_cron_ids(self):
        # Fetches all the active cron ids
        cron_list = []
        if self.ks_aio_cron_id:
            cron_list.append(self.ks_aio_cron_id.id)
        if self.ks_aus_cron_id:
            cron_list.append(self.ks_aus_cron_id.id)
        if self.ks_auos_cron_id:
            cron_list.append(self.ks_auos_cron_id.id)
        if self.ks_aip_cron_id:
            cron_list.append(self.ks_aip_cron_id.id)
        if self.ks_aeps_cron_id:
            cron_list.append(self.ks_aeps_cron_id.id)
        if self.ks_aps_cron_id:
            cron_list.append(self.ks_aps_cron_id.id)
        if self.ks_acs_cron_id:
            cron_list.append(self.ks_acs_cron_id.id)
        if self.ks_aep_cron_id:
            cron_list.append(self.ks_aep_cron_id.id)
        if self.ks_ausp_cron_id:
            cron_list.append(self.ks_ausp_cron_id.id)
        return cron_list

    def action_all_crons(self):
        # action window returns all the crons
        all_cron_ids = self.get_all_cron_ids()
        action = {
            'domain': [('id', 'in', all_cron_ids), ('active', 'in', (True, False))],
            'name': 'WooCommere Schedulers',
            'view_mode': 'tree,form',
            'res_model': 'ir.cron',
            'type': 'ir.actions.act_window',
        }
        return action

    def action_active_crons(self):
        # action window returns all the active crons
        all_cron_ids = self.get_all_cron_ids()
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommere Schedulers',
            'res_model': 'ir.cron',
            'domain': [('id', 'in', all_cron_ids), ('active', '=', True)],
            'view_mode': 'tree,form',
        }

    def action_all_pricelists(self):
        # action window returns for pricelists
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommere Price Lists',
            'res_model': 'product.pricelist',
            'domain': [('id', 'in', self.ks_woo_pricelist_ids.ids), ('ks_wc_instance', '=', self.id)],
            'view_mode': 'tree,form',
            'help': """<p class="o_view_nocontent_empty_folder">{}</p>""".format(_('All the pricelist created for '
                                                                                   'WooCommerce Instances will appear '
                                                                                   'here'))
        }

    def ks_woo_activate_instance(self):
        # Activates the instance
        if self.ks_instance_connected and self.ks_instance_state == 'connected':
            self.ks_instance_state = 'active'
            shipping_method_json_records = self.env[
                'ks.woo.delivery.carrier'].ks_woo_get_all_shipping_methods(instance_id=self)
            attribute_json_records = self.env['ks.woo.product.attribute'].ks_woo_get_all_attributes(
                instance_id=self)
            category_json_records = self.env['ks.woo.product.category'].ks_woo_get_all_product_category(
                instance=self)
            pg_json_records = self.env['ks.woo.payment.gateway'].ks_woo_get_all_payment_gateway(
                instance=self)
            if pg_json_records:
                self.env['ks.woo.queue.jobs'].ks_create_pg_record_in_queue(instance=self,
                                                                           data=pg_json_records)
            if category_json_records:
                self.env['ks.woo.queue.jobs'].ks_create_category_record_in_queue(instance=self,
                                                                                 data=category_json_records)

            if attribute_json_records:
                self.env['ks.woo.queue.jobs'].ks_create_attribute_record_in_queue(instance=self,
                                                                                  data=attribute_json_records)
            if shipping_method_json_records:
                self.env['ks.woo.queue.jobs'].ks_create_shipping_record_in_queue(instance=self,
                                                                                 data=shipping_method_json_records)

            return self.env["ks.message.wizard"].ks_pop_up_message("Active",
                                                                   "Instance  Activated")

    def ks_woo_deactivate_instance(self):
        # Deactivate the instance
        if self.ks_instance_connected and self.ks_instance_state == 'active':
            self.ks_instance_state = 'deactivate'
            return self.env["ks.message.wizard"].ks_pop_up_message("Deactivated",
                                                                   "Instance  Deactivated")

    def ks_woo_api_authentication(self):

        """
        Method to setup the api
        :return: woo_api object
        """
        woo_api = WC_API(
            url=self.ks_store_url,
            consumer_key=self.ks_customer_key,
            consumer_secret=self.ks_customer_secret,
            wp_api=True,
            version=self.ks_version,
            verify_ssl=self.ks_verify_ssl,
            timeout=50,
            query_string_auth=self.ks_auth

        )
        return woo_api

    def ks_woo_connect_to_instance(self):
        """
        This will Connect the Odoo Instance to WooCommerce and Return the Pop-up window
        with the Response
        :return: ks.message.wizard() Action window with response message or Validation Error Pop-up
        """
        try:
            woo_api = self.ks_woo_api_authentication()
            if woo_api.get("").status_code == 200:
                woo_api.get("").json()  # To check if we are getting correct response from the Instance URL
                message = 'Connection Successful'
                names = 'Success'
                self.ks_instance_connected = True
                self.ks_instance_state = 'connected'
                if self.env.company:
                    self.ks_warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).id
                if self.ks_warehouse:
                    self.ks_location_id = self.ks_warehouse.lot_stock_id.id
                    self.ks_sales_person = self.env.user.id
                self.ks_woo_currency = self.env.user.currency_id.id
                self.ks_stock_field_type = self.env['ir.model.fields'].search([('name','=','free_qty')]).ids[0]
                for sales_team in self.env['crm.team'].search([]):
                    if sales_team.member_ids.ids and self.ks_sales_person.id in sales_team.member_ids.ids:
                        self.ks_sales_team =sales_team.id
                if len(self.ks_webhook_conf) == 0:
                    self.ks_manage_webhooks()
            else:
                message = (str(woo_api.get("").status_code) + ': ' + eval(woo_api.get("").text).get('message')) if len(
                    woo_api.get("").text.split(
                        "woocommerce_rest_authentication_error")) > 1 else 'Please enter the Valid WooCommerce Store URL.'
                if message == '401: Consumer key is invalid.':
                    message = "Customer Key is Invalid"
                if message == '401: Invalid signature - provided signature does not match.':
                    message = "Customer Secret Key is Invalid"
                names = 'Error'
            return self.env["ks.message.wizard"].ks_pop_up_message(names, message)
        except (ConnectionError, ValueError):
            raise ValidationError(
                "Couldn't Connect the instance !! Please check the network connectivity or the configuration or Store "
                "URL "
                " parameters are "
                "correctly set.")
        except Exception as e:
            raise ValidationError(_(e))

    def ks_woo_update_the_response(self, json_data, odoo_record, woo_id_field, other_data=False):

        """
        Updates any extra data from woocommrece to layer models
        :param json_data: api response json data
        :param odoo_record: layer model domain
        :param woo_id_field: woo unique id storage field
        :param other_data: dict(of extra data)
        """
        data = {woo_id_field: json_data.get("id") or ""}
        if woo_id_field == 'ks_woo_order_id':
            line_ids = [line['id'] for line in json_data['line_items']]
            count = 0
            for lines in odoo_record.order_line:
                if not lines.ks_woo_order_line_id:
                    lines.ks_woo_order_line_id = line_ids[count]
                    count += 1
        elif woo_id_field == 'ks_woo_partner_id':
            odoo_record.ks_res_partner.write({
                'company_id':odoo_record.ks_company_id.id,
            })
        elif woo_id_field == 'ks_woo_product_id':
            odoo_record.ks_product_template.write({
                'company_id': odoo_record.ks_company_id.id,
            })
        if json_data.get('date_modified'):
            data.update({
                "ks_date_updated": datetime.strptime((json_data.get('date_modified')).replace('T', ' '),
                                                     DEFAULT_SERVER_DATETIME_FORMAT),
            })
        if json_data.get('date_created'):
            data.update({
                "ks_date_created": datetime.strptime((json_data.get('date_created') or False).replace('T', ' '),
                                                     DEFAULT_SERVER_DATETIME_FORMAT)
            })
        if other_data:
            data.update(other_data)
        if odoo_record:
            odoo_record.write(data)

    def open_specific_operation_form_action(self):
        # Opens operations wizard with current instance in context
        view = self.env.ref('ks_woocommerce.ks_specific_operations_form_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Operations',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'ks.woo.instance.operations',
            'view_mode': 'form',
            'context': {'default_ks_instances': [(6, 0, [self.id])], 'default_woo_instance': True,
                        "default_ks_check_multi_operation": False},
            'target': 'new',
        }

    def action_reset_credentials(self):
        #action window returns for resetting the credentials
        view = self.env.ref('ks_woocommerce.ks_reset_credentials_form_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reset Credentials',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'ks.woo.reset.credentials',
            'view_mode': 'form',
            'context': {'default_ks_instances': self.id,
                        },
            'target': 'new',
        }

    def open_multiple_operation_form_action(self):
        # Opens operations wizard with current instance in context
        view = self.env.ref('ks_woocommerce.ks_multiple_operations_form_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Operations',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'ks.woo.instance.operations',
            'view_mode': 'form',
            'context': {'default_ks_instances': [(6, 0, [self.id])], 'default_woo_instance': True,
                        "default_ks_check_multi_operation": True},
            'target': 'new',
        }

    def ks_open_woo_configuration(self):
        # Action window to open configurations
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Operations',
            'view': 'form',
            'res_id': self.id,
            'res_model': 'ks.woo.connector.instance',
            'view_mode': 'form',
        }

    def ks_open_instance_logs(self):
        # Action window to open logs
        action = self.env.ref('ks_woocommerce.ks_woo_logs_action').sudo().read()[0]
        action['domain'] = [('ks_woo_instance.id', '=', self.id)]
        return action

    def prepare_hook_data_for_odoo(self, webhook_data):

        """
        Webhook data preparation
        :param webhook_data: api json data
        :return: odoo model compatible data
        """
        topic = webhook_data.get("topic")
        topic = topic[:-1]
        topic = topic.split(".")
        topic = "_".join(topic)
        vals = {
            'name': webhook_data.get("name"),
            'status': webhook_data.get("status"),
            'base_url': webhook_data.get("delivery_url"),
            'ks_woo_id': webhook_data.get("id"),
            'operations': topic,
            'ks_instance_id': self.id
        }
        return vals

    def ks_sync_webhooks(self):
        # Refresh the webhook, for any updation
        webhook_data = self.env['ks.webhooks.configuration'].ks_get_all_webhooks(self)
        for each_data in webhook_data:
            woo_id = each_data.get("id")
            to_update_data = self.prepare_hook_data_for_odoo(each_data)
            if self.ks_webhook_conf.search([('ks_woo_id', '=', woo_id), ('ks_instance_id', '=', self.id)]):
                record_id = self.ks_webhook_conf.search([('ks_woo_id', '=', woo_id), ('ks_instance_id', '=', self.id)]).id
                self.ks_webhook_conf = [(1, record_id, to_update_data)]

    def ks_open_woo_orders(self):
        """
        opens orders for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_sale_order').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id)]
        return action

    def ks_open_woo_products(self):
        """
        opens products for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_template_').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id)]
        return action

    def ks_open_woo_coupons(self):

        """
        opens coupons for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_ks_woo_coupon').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id)]
        return action

    def ks_open_woo_customers(self):

        """
        opens customer for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_ks_woo_partner').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id)]
        return action

    ks_exported_counts = fields.Integer(compute='_compute_counts_for_domains', string = "Counts Exported")
    ks_ready_exported_counts = fields.Integer(compute='_compute_counts_for_domains', string = "Counts  Ready")
    ks_published_counts = fields.Integer(compute='_compute_counts_for_domains', string = "Counts Published")
    ks_unpublished_counts = fields.Integer(compute='_compute_counts_for_domains', string = "Counts Unpublished")
    ks_quotation_counts = fields.Integer(compute='_compute_counts_for_domains', string = "Counts Quotation")
    ks_orders_counts = fields.Integer(compute='_compute_counts_for_domains', string = "Counts Orders")
    ks_waiting_available_count = fields.Integer(string = "Counts Wait")
    ks_partially_available_count = fields.Integer(string = "Counts Partial")
    ks_ready_transfer_count = fields.Integer(string = "Counts Ready")
    ks_transferred_count = fields.Integer(string = "Counts Transfered")
    ks_open_count = fields.Integer(compute='_compute_counts_for_domains', string = "Counts open")
    ks_paid_count = fields.Integer(compute='_compute_counts_for_domains', string = "Counts paid")
    ks_refund_count = fields.Integer(compute='_compute_counts_for_domains', string = "Counts refund")

    def _compute_counts_for_domains(self):
        # counts the sub domains for instance wise domains
        for rec in self:
            rec.ks_exported_counts = rec.env['ks.woo.product.template'].search_count([
                ('ks_wc_instance', '=', rec.id), ('ks_product_template', '!=', False)])
            rec.ks_ready_exported_counts = rec.env['ks.woo.product.template'].search_count([
                ('ks_wc_instance', '=', rec.id), ('ks_product_template', '=', False)])
            rec.ks_published_counts = rec.env['ks.woo.product.template'].search_count([
                ('ks_wc_instance', '=', rec.id), ('ks_product_template', '!=', False),
                ('ks_published', '=', True)])
            rec.ks_unpublished_counts = rec.env['ks.woo.product.template'].search_count([
                ('ks_wc_instance', '=', rec.id), ('ks_product_template', '!=', False),
                ('ks_published', '=', False)])
            rec.ks_quotation_counts = rec.env['sale.order'].search_count([
                ('ks_wc_instance', '=', rec.id), ('state', '=', 'draft')])
            rec.ks_orders_counts = rec.env['sale.order'].search_count([
                ('ks_wc_instance', '=', rec.id), ('state', '=', 'sale')])
            rec.ks_waiting_available_count = rec.env['stock.picking'].search_count([
                ('state', '=', 'waiting'), ('sale_id.ks_wc_instance', '=', rec.id),
                ('sale_id.ks_woo_order_id', '>', 0)])
            rec.ks_partially_available_count = rec.env['stock.picking'].search_count(
                [('state', '=', 'confirmed'), ('sale_id.ks_wc_instance', '=', rec.id),
                 ('sale_id.ks_woo_order_id', '>', 0)])
            rec.ks_ready_transfer_count = rec.env['stock.picking'].search_count(
                [('state', '=', 'assigned'), ('sale_id.ks_wc_instance', '=', rec.id),
                 ('sale_id.ks_woo_order_id', '>', 0)])
            rec.ks_transferred_count = rec.env['stock.picking'].search_count([
                ('state', '=', 'done'), ('sale_id.ks_wc_instance', '=', rec.id), ('sale_id.ks_woo_order_id', '>', 0)])
            rec.ks_open_count = rec.env['account.move'].search_count([
                ('state', '=', 'draft'), ('ks_woo_order_id.ks_wc_instance', '=', rec.id),
                ('ks_woo_order_id', '!=', False)])
            rec.ks_paid_count = rec.env['account.move'].search_count([
                ('payment_state', '=', 'paid'), ('ks_woo_order_id.ks_wc_instance', '=', rec.id),
                ('ks_woo_order_id', '!=', False)])
            rec.ks_refund_count = rec.env['account.move'].search_count([
                ('payment_state', '=', 'reversed'), ('ks_woo_order_id.ks_wc_instance', '=', rec.id),
                ('ks_woo_order_id', '!=', False)])

    def open_exported(self):

        """
        opens exported products for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_template_').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id), ('ks_woo_product_id', '!=', 0)]
        return action

    def open_ready_to_export(self):

        """
        opens ready to export products for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_template_').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id), ('ks_woo_product_id', '=', 0)]
        return action

    def open_published(self):

        """
        opens published products for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_template_').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id), ('ks_published', '=', True)]
        return action

    def open_unpublished(self):

        """
        opens Unpublished products for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_template_').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id), ('ks_published', '=', False)]
        return action

    def open_quotations(self):

        """
        opens orders quotations for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_sale_order').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id), ('state', '=', 'draft')]
        return action

    def open_orders(self):

        """
        opens orders for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_sale_order').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id), ('state', '=', 'sale')]
        return action

    def open_sales_analysis(self):

        """
        opens sales analysis for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_sales_report_all').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id)]
        return action

    def open_payment_method(self):

        """
        opens payment method for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woo_payment_gateway').sudo().read()[0]
        action['domain'] = [('ks_wc_instance', '=', self.id)]
        return action

    def open_waiting_available(self):

        """
        opens waiting available deliveries for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_deliveries').sudo().read()[0]
        action['domain'] = [('sale_id.ks_wc_instance', '=', self.id),
                            ('sale_id.ks_woo_order_id', 'not in', [False, 0]), ('state', '=', 'waiting')]
        return action

    def open_partially_available(self):

        """
        opens partially available deliveries for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_deliveries').sudo().read()[0]
        action['domain'] = [('sale_id.ks_wc_instance', '=', self.id),
                            ('sale_id.ks_woo_order_id', 'not in', [False, 0]), ('state', '=', 'confirmed')]
        return action

    def open_ready_transfer(self):

        """
        opens ready to transfer deliveries for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_deliveries').sudo().read()[0]
        action['domain'] = [('sale_id.ks_wc_instance', '=', self.id),
                            ('sale_id.ks_woo_order_id', 'not in', [False, 0]), ('state', '=', 'assigned')]
        return action

    def open_transferred(self):

        """
        opens transfered deliveries for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_deliveries').sudo().read()[0]
        action['domain'] = [('sale_id.ks_wc_instance', '=', self.id),
                            ('sale_id.ks_woo_order_id', 'not in', [False, 0]), ('state', '=', 'done')]
        return action

    def open_invoice(self):

        """
         opens open invoices for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_invoices').sudo().read()[0]
        action['domain'] = [('state', '=', 'draft'), ('ks_woo_order_id', 'not in', [False, 0]),
                            ('ks_woo_order_id.ks_wc_instance', '=', self.id)]
        return action

    def open_paid_invoice(self):

        """
        opens paid invoices for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_invoices').sudo().read()[0]
        action['domain'] = [('payment_state', '=', 'paid'), ('ks_woo_order_id', 'not in', [False, 0]),
                            ('ks_woo_order_id.ks_wc_instance', '=', self.id)]
        return action

    def open_refund_invoice(self):

        """
        opens refund invoices for current instance
        :return: action
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_invoices').sudo().read()[0]
        action['domain'] = [('payment_state', '=', 'reversed'), ('ks_woo_order_id', 'not in', [False, 0]),
                            ('ks_woo_order_id.ks_wc_instance', '=', self.id)]
        return action


class KSWooIRCronInherit(models.Model):
    _inherit = 'ir.cron'

    ks_wc_instance = fields.Many2one('ks.woo.connector.instance', string='Instance', readonly=True,
                                     ondelete='cascade')

    def cron_initiate(self):
        try:
            cron_record = self.env.ref('ks_woocommerce.ks_ir_cron_job_process')
            if cron_record:
                next_exc_time = datetime.now()
                cron_record.sudo().write({'nextcall': next_exc_time, 'active': True})
        except UserError as e:
            _logger.warning("Cron Initiate error: %s", e)