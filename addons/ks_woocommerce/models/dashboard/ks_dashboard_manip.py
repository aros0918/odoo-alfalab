import json

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class KsDashboard(models.Model):
    _name = 'ks.woo.dashboard'
    _description = "WooCommerce Dashboard"

    ks_wc_instance = fields.One2many("ks.woo.connector.instance", 'ks_dashboard_id',
                                     string="Instance", readonly=True,
                                     help=("WooCommerce Connector Instance reference"))
    color = fields.Integer(string='Color Index', default=10)
    name = fields.Char(string='Name', default='dashboard')
    ks_chart_data = fields.Text(string="Chart Data", default=0, compute='_fetch_graph_data')
    ks_chart_data_pie = fields.Text(string="Pie Chart Data", default=0, compute='_fetch_graph_data')
    ks_graph_view = fields.Integer(string="Graph view", default=1)
    ks_customer_counts = fields.Integer(compute='_compute_count')
    search_domain = fields.Text()
    ks_instance_counts = fields.Integer(compute='_compute_count_instance')

    ks_product_counts = fields.Integer(compute='_compute_count')
    ks_order_counts = fields.Integer(compute='_compute_count')
    ks_invoice_counts = fields.Integer(compute='_compute_count')
    ks_variant_counts = fields.Integer(compute='_compute_count')
    ks_attribute_counts = fields.Integer(compute='_compute_count')
    ks_refund_counts = fields.Integer(compute='_compute_count')
    ks_tag_counts = fields.Integer(compute='_compute_count')
    ks_delivery_counts = fields.Integer(compute='_compute_count')
    ks_category_counts = fields.Integer(compute='_compute_count')
    ks_gateway_counts = fields.Integer(compute='_compute_count')
    ks_coupon_counts = fields.Integer(compute='_compute_count')
    ks_inventory_counts = fields.Integer(compute='_compute_count')

    @api.model
    def fields_get(self, fields=None,attributes=None,allfields=None):
        fields_to_hide = ['id', 'create_uid', 'color', 'ks_graph_view', 'name', 'create_date', 'write_uid',
                          'write_date', 'search_domain']
        res = super(KsDashboard, self).fields_get(allfields)
        for field in fields_to_hide:
            res[field]['searchable'] = False
            res[field]['sortable'] = False
        return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        rec = super(KsDashboard, self).search_read()
        if domain:
            self = self.env['ks.woo.dashboard'].search([])
            if len(self) > 1:
                raise ValidationError("Fatal Error on Dashboard Records")
            self.write({
                'search_domain': domain
            })
            ks_customer_counts, ks_product_counts, ks_order_counts, ks_invoice_counts, ks_variant_counts, \
            ks_attribute_counts, ks_refund_counts, ks_tag_counts, ks_delivery_counts, \
            ks_category_counts, ks_gateway_counts, ks_coupon_counts, ks_inventory_counts = self._compute_count(domain)

            ks_instance_counts = self._compute_count_instance(domain)
            rec[0].update({
                'ks_customer_counts': ks_customer_counts,
                'ks_instance_counts': ks_instance_counts,
                'ks_product_counts': ks_product_counts,
                'ks_order_counts': ks_order_counts,
                'ks_invoice_counts': ks_invoice_counts,
                'ks_variant_counts': ks_variant_counts,
                'ks_attribute_counts': ks_attribute_counts,
                'ks_refund_counts': ks_refund_counts,
                'ks_tag_counts': ks_tag_counts,
                'ks_delivery_counts': ks_delivery_counts,
                'ks_category_counts': ks_category_counts,
                'ks_gateway_counts': ks_gateway_counts,
                'ks_coupon_counts': ks_coupon_counts,
                'ks_inventory_counts': ks_inventory_counts
            })
        print(self.ks_customer_counts)
        return rec

    def _fetch_graph_data(self):
        '''
        {"labels": ["20 February 2019", "23 February 2019", "09 March 2019", "23 March 2019", "23 April 2019",
        "27 April 2019", "14 May 2019", "25 May 2019", "19 June 2019", "29 June 2019", "20 July 2019", "25 July 2019",
        "11 August 2019", "17 August 2019", "07 September 2019", "21 September 2019", "18 October 2019",
        "23 October 2019", "13 November 2019", "22 November 2019", "10 December 2019", "19 December 2019",
        "15 January 2020", "24 January 2020", "11 February 2020", "25 February 2020", "25 March 2020", "07 April 2020",
        "11 December 2020", "12 December 2020", "13 December 2020", "14 December 2020", "15 December 2020",
        "16 December 2020", "17 December 2020"],
        "datasets": [{"data": [320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0,
        320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 320.0, 640.0, 320.0, 4800.0, 6400.0,
        640.0, 320.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "label": "E-COM07 Large Cabinet/Previous"},
        {"data": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1913.1751759196936, 864.3191866560376, 467.88584237179487,
        619.9715699757315, 707.7056399383516, 688.6838666990753, 670.7339998648316],
        "label": "E-COM07 Large Cabinet/Forecast"}]}'''

        ks_raw_data = {}
        labels = {"labels": ['Products', 'Variants', 'Attributes', 'Categories', 'Tags', 'Coupons', 'Customers',
                             'Orders', 'Delivery', 'Invoices', 'Refunds', 'Gateways']}
        labels_pie = {"labels": []}
        ks_raw_data_pie = {}
        ks_raw_data_pie.update(labels_pie)
        ks_raw_data.update(labels)
        datasets = {"datasets": []}
        new_points = []
        progress_points = []
        done_points = []
        failed_points = []
        new_data = {}
        progress_data = {}
        done_data = {}
        failed_data = {}
        # For Product
        ks_product_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'product_template'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_product_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'product_template'), ('state', '=', 'progress'),
             ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_product_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'product_template'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_product_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'product_template'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Variants
        ks_variant_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'product_product'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_variant_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'product_product'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_variant_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'product_product'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_variant_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'product_product'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Attributes
        ks_attribute_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'attribute'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_attribute_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'attribute'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_attribute_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'attribute'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_attribute_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'attribute'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Category
        ks_category_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'category'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_category_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'category'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_category_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'category'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_category_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'category'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Tags
        ks_tag_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count([
            ('ks_model', '=', 'tag'), ('state', '=', 'new')
        , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_tag_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'tag'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_tag_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'tag'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_tag_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'tag'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Coupons
        ks_coupon_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'coupon'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_coupon_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'coupon'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_coupon_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'coupon'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_coupon_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'coupon'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Customers
        ks_customer_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'customer'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_customer_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'customer'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_customer_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'customer'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_customer_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'customer'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Orders
        ks_order_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'sale_order'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_order_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'sale_order'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_order_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'sale_order'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_order_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'sale_order'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Delivery
        ks_delivery_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'delivery'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_delivery_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'delivery'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_delivery_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'delivery'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_delivery_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'delivery'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Invoices
        ks_invoice_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'invoice'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_invoice_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'invoice'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_invoice_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'invoice'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_invoice_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'invoice'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Refunds
        ks_refund_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'refund'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_refund_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'refund'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_refund_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'refund'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_refund_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'refund'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        # For Payment Gateway
        ks_payment_new_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'payment_gateway'), ('state', '=', 'new')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_payment_progress_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'payment_gateway'), ('state', '=', 'progress')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_payment_done_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'payment_gateway'), ('state', '=', 'done')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])
        ks_payment_failed_count = self.env['ks.woo.queue.jobs'].sudo().search_count(
            [('ks_model', '=', 'payment_gateway'), ('state', '=', 'failed')
             , ('ks_wc_instance.ks_company_id', '=', self.env.company.id)])

        new_points.extend([ks_product_new_count, ks_variant_new_count, ks_attribute_new_count, ks_category_new_count,
                           ks_tag_new_count, ks_coupon_new_count, ks_customer_new_count, ks_order_new_count,
                           ks_delivery_new_count, ks_invoice_new_count, ks_refund_new_count, ks_payment_new_count])
        progress_points.extend([ks_product_progress_count, ks_variant_progress_count, ks_attribute_progress_count,
                                ks_category_progress_count,
                                ks_tag_progress_count, ks_coupon_progress_count, ks_customer_progress_count,
                                ks_order_progress_count,
                                ks_delivery_progress_count, ks_invoice_progress_count, ks_refund_progress_count,
                                ks_payment_progress_count])
        done_points.extend(
            [ks_product_done_count, ks_variant_done_count, ks_attribute_done_count, ks_category_done_count,
             ks_tag_done_count, ks_coupon_done_count, ks_customer_done_count, ks_order_done_count,
             ks_delivery_done_count, ks_invoice_done_count, ks_refund_done_count, ks_payment_done_count])
        failed_points.extend(
            [ks_product_failed_count, ks_variant_failed_count, ks_attribute_failed_count, ks_category_failed_count,
             ks_tag_failed_count, ks_coupon_failed_count, ks_customer_failed_count, ks_order_failed_count,
             ks_delivery_failed_count, ks_invoice_failed_count, ks_refund_failed_count, ks_payment_failed_count])

        new_data.update({"data": new_points, "label": "New State"})
        datasets['datasets'].append(new_data)
        progress_data.update({"data": progress_points, "label": "Progress State"})
        datasets['datasets'].append(progress_data)
        done_data.update({"data": done_points, "label": "Completed State"})
        datasets['datasets'].append(done_data)
        failed_data.update({"data": failed_points, "label": "Failed State"})
        datasets['datasets'].append(failed_data)

        ks_raw_data.update(datasets)
        ks_raw_data_pie.update(datasets)
        json_dump_for_pie = json.dumps(ks_raw_data_pie)
        self.ks_chart_data_pie = json_dump_for_pie
        json_dump = json.dumps(ks_raw_data)
        self.ks_chart_data = json_dump
        y = self.ks_chart_data

    def _compute_count_instance(self, domain=False):
        search_domain = domain
        if not domain:
            self.ks_instance_counts = self.ks_wc_instance.search_count([])
        else:
            if len(search_domain) == 1 and search_domain[0][0] == 'ks_wc_instance' and not search_domain[0][2]:
                search_domain = []
            self.ks_instance_counts = self.ks_wc_instance.search_count(search_domain)
        return self.ks_instance_counts

    def _compute_count(self, domain=False):
        if not self:
            self = self.env['ks.woo.dashboard'].search([])
            if len(self) > 1:
                raise ValidationError("Fatal Error on Dashboard Records")
        if not domain:
            domain = []
            self.search_domain = False
        self.ks_customer_counts = self.env['ks.woo.partner'].search_count(domain)
        self.ks_product_counts = self.env['ks.woo.product.template'].search_count(domain)
        self.ks_order_counts = self.env['sale.order'].search_count(domain)
        invoice_domain = [('ks_woo_order_id', '!=', False), ('move_type', '=', 'out_invoice')] if domain else []
        self.ks_invoice_counts = self.env['account.move'].search_count(invoice_domain)
        self.ks_variant_counts = self.env['ks.woo.product.variant'].search_count(domain)
        self.ks_attribute_counts = self.env['ks.woo.product.attribute'].search_count(domain)
        refund_domain = [('move_type', '=', 'out_refund'), ('ks_woo_order_id', '!=', False)] if domain else []
        self.ks_refund_counts = self.env['account.move'].search_count(refund_domain)
        self.ks_tag_counts = self.env['ks.woo.product.tag'].search_count(domain)
        delivery_domain = [('sale_id.ks_woo_order_id', '>', 0)] if domain else []
        self.ks_delivery_counts = self.env['stock.picking'].search_count(delivery_domain)
        self.ks_category_counts = self.env['ks.woo.product.category'].search_count(domain)
        self.ks_gateway_counts = self.env['ks.woo.payment.gateway'].search_count(domain)
        self.ks_coupon_counts = self.env['ks.woo.coupons'].search_count(domain)
        inventory_domain = [('for_woocommerce', '=', True)] if domain else []
        self.ks_inventory_counts = self.env['stock.quant'].search_count(inventory_domain)
        return self.ks_customer_counts, self.ks_product_counts, self.ks_order_counts, self.ks_invoice_counts, \
               self.ks_variant_counts, self.ks_attribute_counts, self.ks_refund_counts, self.ks_tag_counts, \
               self.ks_delivery_counts, self.ks_category_counts, self.ks_gateway_counts, self.ks_coupon_counts, self.ks_inventory_counts

    def ks_get_domain_parse(self, domain=False):
        domain_parse = []
        if self.search_domain:
            domain = eval(self.search_domain)
            for li in domain:
                if type(li) == list:
                    domain_parse.append(tuple(li))
                else:
                    domain_parse.append(li)
        else:
            domain_parse = domain
        return domain_parse

    def get_ks_instances(self):
        domain_parse = []
        if self.search_domain:
            domain = eval(self.search_domain)
            for li in domain:
                if type(li) == list:
                    domain_parse.append(tuple(li))
                else:
                    domain_parse.append(li)
            if domain_parse:
                for i in range(len(domain_parse)):
                    if isinstance(domain_parse[i], tuple):
                        temp = list(domain_parse[i])
                        temp[0] = 'ks_instance_name'
                        temp = tuple(temp)
                        domain_parse[i] = temp
        action = self.env.ref('ks_woocommerce.action_ks_woo_connector_instance').sudo().read()[0]
        action['domain'] = domain_parse
        return action

    def get_ks_customers(self):
        action = self.env.ref('ks_woocommerce.action_ks_woo_partner').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_products(self):
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_template_').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_variants(self):
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_variants_').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_attributes(self):
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_attribute').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_refunds(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_refund').sudo().read()[0]
        action['domain'] = [('move_type', '=', 'out_refund'), ('ks_woo_order_id', '!=', False)]
        return action

    def get_ks_tags(self):
        action = self.env.ref('ks_woocommerce.action_woo_product_tags').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_categories(self):
        action = self.env.ref('ks_woocommerce.action_ks_woo_product_category').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_orders(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_sale_order_quote').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_coupons(self):
        action = self.env.ref('ks_woocommerce.action_ks_woo_coupon').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_invoices(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_invoices').sudo().read()[0]
        action['domain'] = [('ks_woo_order_id', '!=', False), ('move_type', '=', 'out_invoice')]
        return action

    def get_ks_payment_gateways(self):
        action = self.env.ref('ks_woocommerce.action_woo_payment_gateway').sudo().read()[0]
        action['domain'] = self.ks_get_domain_parse(action['domain'])
        return action

    def get_ks_delivery(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_deliveries').sudo().read()[0]
        action['domain'] = [('sale_id.ks_woo_order_id', '>', 0)]
        return action

    def get_inventory(self):
        action = self.env.ref('ks_woocommerce.action_woocommerce_inventory_adjustments').sudo().read()[0]
        action['domain'] = [('for_woocommerce', '=', True)]
        return action
