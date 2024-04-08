# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
	

class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	price_tax = fields.Float(compute='_compute_amount_tax', string='Tax Amount', store=True)

	@api.depends('quantity', 'price_unit', 'tax_ids')
	def _compute_amount_tax(self):
		for line in self:
			tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
			totals = list(tax_results['totals'].values())[0]
			amount_tax = totals['amount_tax']

			line.update({
				'price_tax': amount_tax,
			})