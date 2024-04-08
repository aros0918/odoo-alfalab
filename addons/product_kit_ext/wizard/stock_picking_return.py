# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    def create_returns(self):
        """
            Override Create_returns Method
        """
        ctx = dict(self.env.context)
        if ctx.get('active_id'):
            picking_id = self.env['stock.picking'].browse(ctx['active_id'])
            move_lines = picking_id.move_ids.filtered(lambda move: move.is_kit and move.sale_line_id.id in self.product_return_moves.mapped('move_id').mapped('sale_line_id').ids)
            product_returns = self.product_return_moves.mapped('move_id').ids
            values = [x for x in move_lines.ids if x not in product_returns]
            if values:
                raise UserError(_('Please, return all kit products'))
            for rmove in self.product_return_moves.filtered(lambda l: l.move_id and l.move_id.is_kit and l.move_id.sale_line_id and l.move_id.sale_line_id.is_kit):
                subproduct_ids = rmove.move_id.sale_line_id.product_id.sub_product_line_ids.filtered(lambda l: l.product_id.id == rmove.product_id.id)
                order_qty = rmove.move_id.sale_line_id.product_uom_qty * sum(subproduct_ids.mapped('quantity'))
                if rmove.quantity and order_qty:
                    if rmove.quantity != order_qty:
                        raise UserError(_('Please, return all kit product quantity'))
        return super(StockReturnPicking, self).create_returns()


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    is_kit = fields.Boolean('Use as Kit')
