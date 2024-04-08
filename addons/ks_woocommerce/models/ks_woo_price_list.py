# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class KsWooProductPricelistInherit(models.Model):
    _inherit = 'product.pricelist'

    ks_wc_instance = fields.Many2one('ks.woo.connector.instance', string='WooCommerce Instance ID',
                                     help="""WooCommerce Instance: The Instance which will used this price list to update the price""",
                                     ondelete='cascade')
    ks_wc_regular_pricelist = fields.Boolean("Is Regular pricelist?")
    ks_wc_sale_pricelist = fields.Boolean("Is Sale pricelist?")
