# -*- coding: utf-8 -*-

from odoo import models


class KsBaseProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def ks_get_product_price(self, product, partner=False):
        """
        This function will return the product price from the Price list
        :param product: product.product() object
        :param partner: res.partner() object
        :return: the price of the respective product
        """
        price = self.get_product_price(product, 1.0, partner=partner, uom_id=product.uom_id.id)
        return price

    def ks_set_product_price(self, product_id, price, main_price_list=False, min_qty=1, date_start=False,
                             date_end=False):
        """
        This will set the price on price list item if the item found with all the respective domains otherwise it will
        create a new price list item
        :param product_id: product.product() object
        :param price: price for the product, Type:Float
        :param main_price_list: product.pricelist() object
        :param min_qty: minimum quantity for the product in list, Type:Integer
        :param date_start: date start, Type:Datetime
        :param date_end: end date, Type:Datetime
        :return: product.pricelist.item() object
        """
        domain = [('pricelist_id', '=', self.id), ('product_id', '=', product_id)]
        if min_qty:
            domain.append(('min_quantity', '=', min_qty))
        if date_start:
            domain.append(('date_start', '=', date_start))
        if date_start:
            domain.append(('date_end', '=', date_end))
        product_pricelist_item = self.env['product.pricelist.item'].search(domain)
        if main_price_list:
            # Price will be converted according the conversion rate
            price = self.ks_convert_price_with_currency(main_price_list, price)
        if product_pricelist_item:
            product_pricelist_item.write({'fixed_price': price,
                                          'min_quantity': min_qty,
                                          'date_start': date_start,
                                          'date_end': date_end})
        else:
            values = {
                'pricelist_id': self.id,
                'product_id': product_id,
                'min_quantity': min_qty,
                'fixed_price': price,
                'applied_on': '0_product_variant',
                'date_start': date_start,
                'date_end': date_end
            }
            new_pricelist_item = self.env['product.pricelist.item'].new(values)
            new_pricelist_item._onchange_product_id()
            new_values = self.env['product.pricelist.item']._convert_to_write(
                {name: new_pricelist_item[name] for name in new_pricelist_item._cache})
            product_pricelist_item = self.env['product.pricelist.item'].create(new_values)
        return product_pricelist_item

    def ks_convert_price_with_currency(self, main_price_list, price):
        """
        THis function will convert the price on the basis of the conversion rate
        :param main_price_list: product.pricelist() object
        :param price: Price to be converted
        :return: the converted price
        """
        conversion_rate = self.currency_id.rate / main_price_list.currency_id.rate
        computed_price = price * conversion_rate
        return computed_price