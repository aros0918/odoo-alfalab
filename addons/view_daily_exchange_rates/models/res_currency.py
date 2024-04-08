# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _



class Currency(models.Model):
    _inherit = "res.currency"


    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        currency_rates = (from_currency + to_currency)._get_rates(company, date)
        if not self._context.get('apply'):
            res = currency_rates.get(to_currency.id) / currency_rates.get(from_currency.id)
        if self._context.get('apply') and self._context.get('active_model') == 'sale.order':
            order_rate = self.env['sale.order'].browse(self._context.get('active_id')).currency_rate
            res =  order_rate / currency_rates.get(from_currency.id)
        if self._context.get('apply') and self._context.get('active_model') == 'account.move':
            current_rate  =  self.env['account.move'].browse(self._context.get('active_id')).current_rate
            res =  current_rate / currency_rates.get(from_currency.id)
        return res

    def _convert(self, from_amount, to_currency, company, date, round=True):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        assert company, "convert amount from unknown company"
        assert date, "convert amount from unknown date"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        elif from_amount:
            to_amount = from_amount * self._get_conversion_rate(self, to_currency, company, date)
        else:
            return 0.0
        return to_currency.round(to_amount) if round else to_amount



class CurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    _sql_constraints = [
            ('unique_name_per_day', 'check(1=1)', 'No error'),
            ('currency_rate_check', 'CHECK (rate>0)', 'The currency rate must be strictly positive.'),
]

    #removing constraint
    def _auto_init(self):
        res =super()._auto_init()
        self.env.cr.execute("""ALTER TABLE res_currency_rate DROP CONSTRAINT IF EXISTS unique_name_per_day;""")
        return res

    #apply rate
    def apply_exchange_rate(self):
        context = self._context.copy()
        context.update({'apply':self.id})
        if self._context.get('active_model') == 'sale.order':
            if self._context.get('active_id'):
                sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
                sale_order.with_context(context)._compute_currency_rate()
                for line in sale_order.order_line:
                    line.with_context(context)._compute_price_unit()
        if self._context.get('active_model') == 'account.move':
            invoice =  self.env['account.move'].browse(self._context.get('active_id'))
            invoice.current_rate = self.rate
            if self._context.get('active_id'):
                account_move = self.env['account.move'].browse(self._context.get('active_id'))
                for line in account_move.invoice_line_ids:
                    line.with_context(context)._compute_price_unit()
