# -*- coding: utf-8 -*-

from odoo import models, fields, api


class KsBaseProductProductInherit(models.Model):
    _inherit = "product.product"

    ks_length = fields.Float()
    ks_width = fields.Float()
    ks_height = fields.Float()
    ks_image_ids = fields.One2many('ks.common.product.images', 'ks_variant_id', string='Images')

    @api.onchange('ks_length', 'ks_width', 'ks_height')
    def onchange_l_b_h(self):
        """
        This will calculate the value for Volume with respective of ks_length, ks_width and ks_height

        :return: None
        """
        self.volume = float(self.ks_length if self.ks_length else 0) * float(
            self.ks_width if self.ks_width else 0) * float(
            self.ks_height if self.ks_height else 0)

    def ks_prepare_common_image_values(self, values):
        """
        This will prepare image dictionary data
        :param values: dictionary of values
        :return: the image dictionary.
        """
        image_values = {"sequence": 0,
                        "ks_image": values.get("image_1920", False),
                        "ks_name": self.name,
                        "ks_variant_id": self.id,
                        "ks_template_id": self.product_tmpl_id.id}
        return image_values

    def ks_get_stock_quantity(self, warehouse, product, stock_field):
        """
        This function will return the stock quantity according to the stock field and warehouse location for the Product
        :param warehouse: stock.warehouse() object
        :param product: product.product() object
        :param stock_field: field name : free_qty or virtual_available
        :return:
        """
        location_ids = self.ks_prepare_location_ids(warehouse)
        stock_qty = 0
        if stock_field == 'free_qty':
            stock_qty = self.ks_get_product_free_qty(location_ids, product.id)
        elif stock_field == 'virtual_available':
            stock_qty = self.ks_get_product_forecasted_qty(product)
        return stock_qty

    def ks_get_product_free_qty(self, location_ids, product_id):
        """
        This will return the free quantity( quantity - reserved_quantity) for the product on the locations
        :param location_ids: stock.location() object
        :param product_id: product.product() object
        :return: qty, Type:Integer
        """
        query = """select COALESCE(sum(sq.quantity)-sum(sq.reserved_quantity),0) as stock
                        from product_product pp
                        left join stock_quant sq on pp.id = sq.product_id and sq.location_id in (%s)
                        where pp.id = %s group by pp.id;""" % (location_ids, product_id)
        self._cr.execute(query)
        result = self._cr.dictfetchall()
        return result[0].get('stock') if result else 0

    def ks_get_product_forecasted_qty(self, product_id):
        """
        This will return the forecast quantity (virtual_available) for the product
        :param product_id: product.product() object
        :return: qty, Type:Integer
        """
        return product_id.virtual_available

    def ks_prepare_location_ids(self, warehouse):
        locations = self.env['stock.location'].search([('location_id', 'child_of', warehouse.lot_stock_id.ids)])
        location_ids = ','.join(str(e) for e in locations.ids)
        return location_ids

    # def action_woo_layer_templates(self):
    #     self.ensure_one()
    #     action = self.env["ir.actions.actions"]._for_xml_id("ks_woocommerce.action_ks_woo_product_template_")
    #     action['domain'] = [('id', 'in', self.ks_product_template.ids)]
    #     return action