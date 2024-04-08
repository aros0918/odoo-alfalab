# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_kit_id = fields.Many2one('product.product', string="Product Kit")
    is_kit = fields.Boolean('Use as Kit', related='product_id.is_kit')

    @api.onchange('is_kit')
    def _onchange_is_kit(self):
        if self.is_kit:
            self.product_kit_id = self.product_id.id

    def _get_outgoing_incoming_moves_kit(self):
        outgoing_moves = self.env['stock.move']
        incoming_moves = self.env['stock.move']

        for move in self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and r.product_id.id in self.product_id.sub_product_line_ids.mapped('product_id').ids):
            if move.location_dest_id.usage == "customer":
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    outgoing_moves |= move
            elif move.location_dest_id.usage != "customer" and move.to_refund:
                incoming_moves |= move

        return outgoing_moves, incoming_moves

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            if line.qty_delivered_method == 'stock_move' and line.is_kit:
                qty = 0.0
                outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves_kit()
                so_out_list, so_in_list = [], []
                for move in outgoing_moves:
                    if move.state != 'done':
                        continue
                    if move.sale_line_id.id in so_out_list:
                        continue
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                    so_out_list.append(move.sale_line_id.id)
                for move in incoming_moves:
                    if move.state != 'done':
                        continue
                    if move.sale_line_id.id in so_in_list:
                        continue
                    qty -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                    so_in_list.append(move.sale_line_id.id)
                line.qty_delivered = qty
