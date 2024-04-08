# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models, _


class SaleReport(models.Model):
    _inherit = 'sale.report'

    product_kit_id = fields.Many2one('product.product', string='Product Kit', readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['product_kit_id'] = "l.product_kit_id"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            l.product_kit_id, t.is_kit"""
        return res
