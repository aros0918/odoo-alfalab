# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.addons.stock.models.stock_rule import ProcurementException


class Picking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        """
        Override Method for all kit product not available then Warring
        """
        
        self.ensure_one()
        if self.move_ids.filtered(lambda move: move.is_kit and move.product_uom_qty != move.quantity_done):
            raise UserError(_('You cannot validate a transfer if no quantites are reserved nor done. To force the transfer, switch in edit more and encode the done quantities.'))
        return super(Picking, self).button_validate()


class StockMove(models.Model):
    _inherit = "stock.move"

    is_kit = fields.Boolean('Use as Kit')


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _run_pull(self, procurements):
        moves_values_by_company = defaultdict(list)
        mtso_products_by_locations = defaultdict(list)
        sub_mtso_products_by_locations = defaultdict(list)
        # sub_moves_values_by_company1 = defaultdict(list)
        # To handle the `mts_else_mto` procure method, we do a preliminary loop to
        # isolate the products we would need to read the forecasted quantity,
        # in order to to batch the read. We also make a sanitary check on the
        # `location_src_id` field.
        for procurement, rule in procurements:
            if not rule.location_src_id:
                msg = _('No source location defined on stock rule: %s!') % (self.name, )
                raise ProcurementException([(procurement, msg)])

            if rule.procure_method == 'mts_else_mto':
                mtso_products_by_locations[rule.location_src_id].append(procurement.product_id.id)

        # Get the forecasted quantity for the `mts_else_mto` procurement.
        forecasted_qties_by_loc = {}
        for location, product_ids in mtso_products_by_locations.items():
            products = self.env['product.product'].browse(product_ids).with_context(location=location.id)
            forecasted_qties_by_loc[location] = {product.id: product.virtual_available for product in products}

        # Prepare the move values, adapt the `procure_method` if needed.
        for procurement, rule in procurements:
            procure_method = rule.procure_method
            if rule.procure_method == 'mts_else_mto':
                qty_needed = procurement.product_uom._compute_quantity(procurement.product_qty, procurement.product_id.uom_id)
                qty_available = forecasted_qties_by_loc[rule.location_src_id][procurement.product_id.id]
                if float_compare(qty_needed, qty_available, precision_rounding=procurement.product_id.uom_id.rounding) <= 0:
                    procure_method = 'make_to_stock'
                    forecasted_qties_by_loc[rule.location_src_id][procurement.product_id.id] -= qty_needed
                else:
                    procure_method = 'make_to_order'
            if procurement.product_id and procurement.product_id.is_kit and procurement.values.get('group_id').id and procurement.values.get('group_id').sale_id:
                for subproduct in procurement.product_id.sub_product_line_ids:
                    product_id = subproduct.product_id
                    name = subproduct.product_id.name
                    product_uom = subproduct.product_id and subproduct.product_id.uom_id
                    qty = subproduct.quantity * procurement.product_qty
                    sub_product_rule = procurement.values['group_id']._get_rule(subproduct.product_id, procurement.location_id, procurement.values)
                    sub_procure_method = sub_product_rule.procure_method
                    if sub_product_rule.procure_method == 'mts_else_mto':
                        sub_mtso_products_by_locations[sub_product_rule.location_src_id].append(subproduct.product_id.id)
                        for location, product_ids in sub_mtso_products_by_locations.items():
                            products = self.env['product.product'].browse(product_ids).with_context(location=location.id)
                            forecasted_qties_by_loc[location] = {product.id: product.virtual_available for product in products}
                        qty_needed = product_id.uom_id._compute_quantity(qty, product_id.uom_id)
                        qty_available = forecasted_qties_by_loc[sub_product_rule.location_src_id][product_id.id]
                        if float_compare(qty_needed, qty_available, precision_rounding=product_id.uom_id.rounding) <= 0:
                            sub_procure_method = 'make_to_stock'
                            forecasted_qties_by_loc[sub_product_rule.location_src_id][product_id.id] -= qty_needed
                        else:
                            sub_procure_method = 'make_to_order'
                    move_values = sub_product_rule._get_stock_move_values(product_id, qty, product_uom, procurement.location_id, name, procurement.origin, procurement.company_id, procurement.values)
                    move_values['procure_method'] = sub_procure_method
                    move_values['is_kit'] = True
                    moves_values_by_company[procurement.company_id.id].append(move_values)
            else:
                move_values = rule._get_stock_move_values(*procurement)
                move_values['procure_method'] = procure_method
                moves_values_by_company[procurement.company_id.id].append(move_values)

        for company_id, moves_values in moves_values_by_company.items():
            # create the move as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
            moves = self.env['stock.move'].with_user(SUPERUSER_ID).sudo().with_company(company_id).create(moves_values)
            # Since action_confirm launch following procurement_group we should activate it.
            moves._action_confirm()
        return True
