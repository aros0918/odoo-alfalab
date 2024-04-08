# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from functools import lru_cache


class AccountMove(models.Model):
    _inherit = 'account.move'

    current_rate = fields.Float(
        string="Current Rate",)
    
    
    def open_currency_form(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_currency_form")
        action['views'] = [(False,'form')]
        action['res_id'] = self.currency_id.id
        action['view_id'] = "base.view_currency_form"
        return action


    @api.onchange('currency_id')
    def _compute_display_inactive_currency_warning_apple(self):
        for move in self.with_context(active_test=False):
            move.display_inactive_currency_warning = move.currency_id and not move.currency_id.active
        move.invoice_line_ids._compute_price_unit()
      

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    # @api.depends('product_id', 'product_uom_id', 'currency_id')
    # def _compute_price_unit(self):
    #     for line in self:
    #         if not line.product_id or line.display_type in ('line_section', 'line_note'):
    #             continue
    #         if line.move_id.is_sale_document(include_receipts=True):
    #             document_type = 'sale'
    #         elif line.move_id.is_purchase_document(include_receipts=True):
    #             document_type = 'purchase'
    #         else:
    #             document_type = 'other'
            
    #         if not self._context.get('apply'):
    #             line.price_unit = line.product_id._get_tax_included_unit_price(
    #                 line.move_id.company_id,
    #                 line.move_id.currency_id,
    #                 line.move_id.date,
    #                 document_type,
    #                 fiscal_position=line.move_id.fiscal_position_id,
    #                 product_currency=line.currency_id,
    #                 product_uom=line.product_uom_id,
    #             )
    #         else:
    #             line.price_unit = line.product_id._get_tax_included_unit_price(
    #                 line.move_id.company_id,
    #                 line.move_id.currency_id,
    #                 line.move_id.date,
    #                 document_type,
    #                 fiscal_position=line.move_id.fiscal_position_id,
    #                 product_currency=line.currency_id,
    #                 product_uom=line.product_uom_id,
    #             )
            
    @api.depends('currency_id', 'company_id', 'move_id.date')
    def _compute_currency_rate(self):
        @lru_cache()
        def get_rate(from_currency, to_currency, company, date):
            return self.env['res.currency']._get_conversion_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                company=company,
                date=date,
            )
        for line in self:
            if line.currency_id:
                line.currency_rate = get_rate(
                    from_currency=line.company_currency_id,
                    to_currency=line.currency_id,
                    company=line.company_id,
                    date=line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line),
                )
            else:
                line.currency_rate = 1
        if self._context.get('apply') and self._context.get('active_model') == 'account.move':
            rate_record = self.env['res.currency.rate'].browse(self._context.get('apply'))
            line.currency_rate = rate_record.rate
