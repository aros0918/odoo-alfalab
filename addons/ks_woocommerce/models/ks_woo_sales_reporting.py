# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo import tools


class KsSaleReport(models.Model):
    _name = "ks.woo.sale.report"
    _description = '''WooCommerce Sales Analysis'''
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    @api.model
    def _get_done_states(self):
        return ['sale', 'done', 'paid']

    name = fields.Char(string='Order Reference', readonly=True)
    date = fields.Datetime(string='Order Date', readonly=True)
    ks_wc_instance = fields.Many2one('ks.woo.connector.instance', string='WooCommerce Instance', readonly=True, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    product_id = fields.Many2one('product.product', string='Product Variant', readonly=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)
    product_uom_qty = fields.Float(string='Qty Ordered', readonly=True)
    qty_delivered = fields.Float(string='Qty Delivered', readonly=True)
    qty_to_invoice = fields.Float(string='Qty To Invoice', readonly=True)
    qty_invoiced = fields.Float(string='Qty Invoiced', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    price_total = fields.Float(string='Total', readonly=True)
    price_subtotal = fields.Float(string='Untaxed Total', readonly=True)
    untaxed_amount_to_invoice = fields.Float(string='Untaxed Amount To Invoice', readonly=True)
    untaxed_amount_invoiced = fields.Float(string='Untaxed Amount Invoiced', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    nbr = fields.Integer(string='# of Lines', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', readonly=True)
    country_id = fields.Many2one('res.country', string='Customer Country', readonly=True)
    industry_id = fields.Many2one('res.partner.industry', string='Customer Industry', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', string='Customer Entity', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Sales Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True)
    weight = fields.Float(string='Gross Weight', readonly=True)
    volume = fields.Float(string='Volume', readonly=True)

    discount = fields.Float(string='Discount %', readonly=True)
    discount_amount = fields.Float(string='Discount Amount', readonly=True)
    campaign_id = fields.Many2one('utm.campaign', string='Campaign')
    medium_id = fields.Many2one('utm.medium', string='Medium')
    source_id = fields.Many2one('utm.source', string='Source')

    order_id = fields.Many2one('sale.order', string='Order #', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause='', where_clause=''):
        """
        Query method to fetch data from database based on instance and other filters
        :param with_clause: psql with clause
        :param fields: fields name
        :param groupby: psql groupby clause
        :param from_clause: psql from clause
        :param where_clause: psql where clause
        :return: postgres query
        """
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            coalesce(min(l.id), -s.id) as id,
            l.product_id as product_id,
            t.uom_id as product_uom,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as product_uom_qty,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_to_invoice / u.factor * u2.factor) ELSE 0 END as qty_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_delivered / u.factor * u2.factor) ELSE 0 END as qty_delivered,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_invoiced / u.factor * u2.factor) ELSE 0 END as qty_invoiced,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as price_total,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as price_subtotal,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.untaxed_amount_invoiced / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount_invoiced,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.untaxed_amount_to_invoice / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount_to_invoice,
            count(*) as nbr,
            s.name as name,
            s.date_order as date,
            s.state as state,
            s.partner_id as partner_id,
            s.company_id as company_id,
            s.campaign_id as campaign_id,
            s.user_id as user_id,
            s.medium_id as medium_id,
            s.source_id as source_id,
            s.warehouse_id as warehouse_id,
            s.ks_wc_instance as ks_wc_instance,
            extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
            t.categ_id as categ_id,
            s.pricelist_id as pricelist_id,
            s.analytic_account_id as analytic_account_id,
            s.team_id as team_id,
            p.product_tmpl_id,
            partner.country_id as country_id,
            partner.industry_id as industry_id,
            partner.commercial_partner_id as commercial_partner_id,
            CASE WHEN l.product_id IS NOT NULL THEN sum(p.weight * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as weight,
            CASE WHEN l.product_id IS NOT NULL THEN sum(p.volume * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as volume,
            l.discount as discount,
            CASE WHEN l.product_id IS NOT NULL THEN sum((l.price_unit * l.product_uom_qty * l.discount / 100.0 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END))ELSE 0 END as discount_amount,
            s.id as order_id
        """

        for field in fields.values():
            select_ += field

        from_ = """
                sale_order_line l
                      right outer join sale_order s on (s.id=l.order_id)
                      join res_partner partner on s.partner_id = partner.id
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join uom_uom u on (u.id=l.product_uom)
                    left join uom_uom u2 on (u2.id=t.uom_id)
                    left join product_pricelist pp on (s.pricelist_id = pp.id)
                %s
        """ % from_clause

        where_ = """l.product_id IS NOT NULL AND NOT s.ks_woo_order_id=0 AND s.ks_wc_instance IS NOT NULL  %s""" % (
            where_clause)

        groupby_ = """
            l.product_id,
            l.order_id,
            t.uom_id,
            t.categ_id,
            s.name,
            s.date_order,
            s.partner_id,
            s.user_id,
            s.state,
            s.company_id,
            s.campaign_id,
            s.medium_id,
            s.source_id,
            s.pricelist_id,
            s.analytic_account_id,
            s.team_id,
            s.ks_wc_instance,
            s.warehouse_id,
            p.product_tmpl_id,
            partner.country_id,
            partner.industry_id,
            partner.commercial_partner_id,
            l.discount,
            s.id %s
        """ % (groupby)
        return '%s (SELECT %s FROM %s WHERE %s GROUP BY %s)' % (with_, select_, from_, where_, groupby_)

    def init(self):
        """
        initiates the query
        :return:
        """
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
