# -*- coding: utf-8 -*-
import traceback
import logging
from datetime import datetime

from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class KsBaseStockInventory(models.Model):
    _inherit = "stock.quant"

    name = fields.Char(
        'Inventory Reference', default="Inventory",
        readonly=True, required=True)

    prefill_counted_quantity = fields.Selection(string='Counted Quantities',
                                                help="Allows to start with a pre-filled counted quantity for each lines or "
                                                     "with all counted quantities set to zero.", default='counted',
                                                selection=[('counted', 'Default to stock on hand'),
                                                           ('zero', 'Default to zero')])

    @api.model
    def ks_create_stock_inventory_adjustment(self, product_data, location_id, auto_validate=False, queue_record = False):
        """
        This create the Inventory adjustment with the products and location
        :param product_data: list of dictionary {"product_id": 0, "product_qty": 0}
        :param location_id: stock.location() object
        :param auto_validate: If given the validate the adjustment created
        :return: stock.quant() if created
        """
        try:
            if product_data:
                inventories = self
                while product_data:
                    inventory_lines = product_data[:100]
                    inventory = self
                    inventory_name = 'product_inventory_%s' % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    new_products_values = []
                    for invent in inventory_lines:
                        p_id = self.env['product.product'].browse(invent['product_id']).id
                        if p_id:
                            inventory_values = {
                                'name': inventory_name,
                                'location_id': location_id.id if location_id else False,
                                'inventory_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'inventory_quantity': invent['product_qty'],
                                'prefill_counted_quantity': 'zero',
                                "company_id": location_id.company_id.id if location_id else self.env.company.id
                            }
                            self = self.env['stock.quant'].search([('product_id', '=', p_id),('location_id','=',location_id.id)])
                            if self:
                                self.write(inventory_values)
                                inventory += self
                            else:
                                inventory_values['product_id'] = p_id
                                inventory += self.create(inventory_values)
                    # inventory.ks_create_inventory_adjustment_lines(inventory_lines, location_id)
                    inventories += inventory
                    del product_data[:100]
                return inventories
            return False
        except Exception as e:
            _logger.error(traceback.format_exc())
            if queue_record:
                queue_record.ks_update_failed_state()
            _logger.info(str(e))
            raise e
            # self.env['ks.woo.logger'].ks_create_odoo_log_param(
            #     ks_operation_performed="create",
            #     ks_model='stock.quant',
            #     ks_layer_model='stock.quant',
            #     ks_message=str(e),
            #     ks_status="failed",
            #     ks_type="stock",
            #     ks_record_id=0,
            #     ks_operation_flow="odoo_to_woo",
            #     ks_woo_id=0,
            #     ks_woo_instance=False)

    # @api.model
    # def ks_create_inventory_adjustment_lines(self, products_data, location_id):
    #     """
    #     Create the inventory adjustment line with the product and the qty in Products data
    #     :param products_data: list of dictionary {"product_id": 0, "product_qty": 0}
    #     :param location_id: stock.location() object
    #     :return: True
    #     """
    #     values_list = []
    #     for product in products_data:
    #         product_id = product.get('product_id')
    #         product_qty = product.get('product_qty')
    #         if product and product_qty:
    #             values = {
    #                 'company_id': self.company_id.id,
    #                 'product_id': product_id,
    #                 'inventory_id': self.id,
    #                 'location_id': location_id.id,
    #                 'product_qty': 0 if product_qty <= 0 else product_qty,
    #             }
    #             values_list.append(values)
    #     # self.env['stock.inventory.line'].create(values_list)
    #     return True
