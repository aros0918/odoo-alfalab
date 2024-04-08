# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'product_uom', 'product_uom_qty','order_id.pricelist_id')

    def _compute_price_unit(self):
        print ("calllllllllllllllllllllllllllllllllll")
        for line in self:
            # check if there is already invoiced amount. if so, the price shouldn't change as it might have been
            # manually edited
            if line.qty_invoiced > 0:
                continue
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
            else:
                price = line.with_company(line.company_id)._get_display_price()
                if not self._context.get('apply'):
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                    line.company_id,
                    line.order_id.currency_id,
                    line.order_id.date_order,
                    'sale',
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id
                )
                else:
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                    line.company_id,
                    line.company_id.currency_id,
                    line.order_id.date_order,
                    'sale',
                    fiscal_position=line.order_id.fiscal_position_id,
                    product_price_unit=price,
                    product_currency=line.currency_id
                )
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def open_currency_form(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_currency_form")
        action['views'] = [(False,'form')]
        action['res_id'] = self.currency_id.id
        action['view_id'] = "base.view_currency_form"
        return action


    @api.onchange('pricelist_id')
    def _onchange_pricelist_id_show_update_prices(self):
        if self.order_line and self.pricelist_id and self._origin.pricelist_id != self.pricelist_id:
            self.show_update_pricelist = True
        for order_line in self.order_line:
            order_line._compute_price_unit()


    @api.depends('currency_id', 'date_order', 'company_id')
    def _compute_currency_rate(self):
        cache = {}
        for order in self:
            order_date = order.date_order.date()
            if not order.company_id:
                order.currency_rate = order.currency_id.with_context(date=order_date).rate or 1.0
                continue
            elif not order.currency_id:
                order.currency_rate = 1.0
            else:
                key = (order.company_id.id, order_date, order.currency_id.id)
                if key not in cache:
                    cache[key] = self.env['res.currency']._get_conversion_rate(
                        from_currency=order.company_id.currency_id,
                        to_currency=order.currency_id,
                        company=order.company_id,
                        date=order_date,
                    )
                if not self._context.get('apply'):
                    order.currency_rate = cache[key]
                else:
                    rate_record = self.env['res.currency.rate'].browse(self._context.get('apply'))
                    order.currency_rate = rate_record.rate
