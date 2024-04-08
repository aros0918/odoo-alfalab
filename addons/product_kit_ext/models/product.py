# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sub_product_line_ids = fields.One2many('sub.product.lines', 'product_tmpl_ref_id', string='Sub Products', copy=False)
    is_kit = fields.Boolean('Use as Kit', copy=False, inherited=False)

    def _prepare_variant_values(self,combination):
        res = super(ProductTemplate, self)._prepare_variant_values(combination)
        res.update({'is_kit':self.is_kit})
        return res


class SubProductLines(models.Model):
    _name = "sub.product.lines"
    _description = "Sub Products"
    _rec_name = "product_id"

    product_id = fields.Many2one('product.product', domain=[('is_kit', '=', False), ('type', '!=', 'service')],
                                string='Product', required=True)
    product_tmpl_ref_id = fields.Many2one('product.template', string='Product Reference', ondelete='cascade')
    quantity = fields.Float('Quantity', default=1)
    standard_price = fields.Float(related='product_id.standard_price')
    lst_price = fields.Float(related='product_id.lst_price')
    qty_available = fields.Float(related='product_id.qty_available')

    _sql_constraints = [
        ('check_quantity', "CHECK((quantity > 0))", "Quantity should be greater than 0."),
    ]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_kit = fields.Boolean('Use as Kit', copy=False)
