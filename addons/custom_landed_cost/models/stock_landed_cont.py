# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def get_no_of_cost_line_id(self,cost_line_id):
        if self.valuation_adjustment_lines:
           cost_line_ids = []
           for lines in self.valuation_adjustment_lines:
               if lines.cost_line_id == cost_line_id:
                   cost_line_ids.append(lines.cost_line_id.id)
           return len(cost_line_ids) 

    
    def is_total_correct(self):
        original_total = 0
        for line in self.cost_lines:
            original_total= original_total + line.price_unit
        adjustment_total = 0 
        for line in self.valuation_adjustment_lines:
            adjustment_total =adjustment_total +  line.additional_landed_cost
        if original_total == adjustment_total:
           return True
        else:
           return {'original_total':original_total,'adjustment_total':adjustment_total}        	

    @api.onchange('valuation_adjustment_lines')
    def _onchange_target_model(self):
        result = self.is_total_correct()
        if result:
            for line in self.valuation_adjustment_lines:
                no_of_product = self.get_no_of_cost_line_id(line.cost_line_id)
                total_cost = line.cost_line_id.price_unit
                line.additional_landed_cost = total_cost/no_of_product  