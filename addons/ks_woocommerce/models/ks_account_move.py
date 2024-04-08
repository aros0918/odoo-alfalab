# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import fields, models, api


class KsAccountInvoiceInherit(models.Model):
    _inherit = 'account.move'

    ks_woo_order_id = fields.Many2one('sale.order', string='WooCommerce Order', help="""WooCommerce Order: The WooCommerce Order""",
                                      readonly=1, ondelete='cascade')
    ks_refunded = fields.Boolean(string="Refunded")
    ks_register_payment = fields.Boolean(string="Refund Payment", default=False)

    def ks_prepare_data_to_refund(self):
        """
        Prepares data to refund on woocommerce
        :return: data
        """
        total_amount = self.amount_total
        time = datetime.today().strftime('%H:%M:%S')
        date = datetime.today().strftime('%Y-%m-%d')
        date_created = date + 'T' + time
        refunded_by = self.user_id.id
        reason_index = self.ref.find(',')
        reason = self.ref[reason_index + 1:] if reason_index != -1 else " "
        data = {
            'date_created': date_created,
            'amount': str(int(total_amount)),
            'reason': reason,
            'refunded_by': refunded_by,
            'api_refund': False
        }
        return data

    def refund_in_woo(self):
        """
        When Refund in woocommerce button is clicked , below method is called
        :return:
        """
        ks_instance_id = self.ks_woo_order_id.ks_wc_instance
        wcapi = ks_instance_id.ks_woo_api_authentication()
        order_id = self.ks_woo_order_id.ks_woo_order_id
        sale_order =  self.ks_woo_order_id
        prepared_data_for_woo = self.ks_prepare_data_to_refund()
        if ks_instance_id.ks_instance_state == 'active':
            try:
                response = wcapi.post("orders/%s/refunds" % order_id, prepared_data_for_woo)
                if response.status_code in [200, 201]:
                    sale_order.write({"ks_woo_status":"refunded"})
                    self.write({"ks_refunded":True})
                    self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                    '''Order Refunded on WooCommerce SuccessFully''')

                    return self.env["ks.message.wizard"].ks_pop_up_message("Refund", "Refund Successful")
                else:
                    self.env['ks.woo.logger'].ks_create_log_param(ks_woo_id=self.ks_woo_order_id.id,
                                                                  ks_operation_performed='refund',
                                                                  ks_type='order',
                                                                  ks_woo_instance=self.ks_woo_order_id.ks_wc_instance,
                                                                  ks_record_id=self.id,
                                                                  ks_message='Order Refunded Failed on Woocommerce' + str(
                                                                      response.content),
                                                                  ks_operation_flow='wl_to_woo',
                                                                  ks_status='failed')
                    return self.env["ks.message.wizard"].ks_pop_up_message("Refund", "Refund Failed")
            except ConnectionError:
                self.env['ks.woo.logger'].ks_create_log_param(ks_woo_id=self.ks_woo_order_id.id,
                                                              ks_operation_performed='refund',
                                                              ks_type='system_status',
                                                              ks_woo_instance=self.ks_woo_order_id.ks_wc_instance,
                                                              ks_record_id=self.id,
                                                              ks_message='Fatal Error Connection Error' + str(
                                                                  ConnectionError),
                                                              ks_operation_flow='wl_to_woo',
                                                              ks_status='failed')
                return self.env["ks.message.wizard"].ks_pop_up_message("Refund", "Refund Failed")
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param(ks_woo_id=self.ks_woo_order_id.id,
                                                              ks_operation_performed='refund',
                                                              ks_type='system_status',
                                                              ks_woo_instance=self.ks_woo_order_id.ks_wc_instance,
                                                              ks_record_id=self.id,
                                                              ks_message='Fatal Error' + str(e),
                                                              ks_operation_flow='wl_to_woo',
                                                              ks_status='failed',
                                                              ks_error=e)
                return self.env["ks.message.wizard"].ks_pop_up_message("Refund", "Refund Failed")
        else:
            self.env['ks.woo.logger'].ks_create_log_param(ks_woo_id=self.ks_woo_order_id.id,
                                                          ks_operation_performed='refund',
                                                          ks_type='system_status',
                                                          ks_woo_instance=self.ks_woo_order_id.ks_wc_instance,
                                                          ks_record_id=self.id,
                                                          ks_message='Instance not active. Please Check Instance Connection',
                                                          ks_operation_flow='wl_to_woo',
                                                          ks_status='failed')

            return self.env["ks.message.wizard"].ks_pop_up_message("Refund",
                                                                   '''Refund Failed, Instance not Connected''')

    @api.model
    def _get_invoice_in_payment_state(self):
        ''' Hook to give the state when the invoice becomes fully paid. This is necessary because the users working
        with only invoicing don't want to see the 'in_payment' state. Then, this method will be overridden in the
        accountant module to enable the 'in_payment' state. '''
        if self.move_type == 'out_refund':
            self.ks_register_payment = True
        res = super(KsAccountInvoiceInherit, self)._get_invoice_in_payment_state()
        return res


class KsAccountTaxInherit(models.Model):
    _inherit = 'account.tax'

    ks_woo_id = fields.Integer('Woo Id',
                               readonly=True, default=0,
                               help="""Woo Id: Unique WooCommerce resource id for the tax on the specified 
                                       WooCommerce Instance""")
    ks_wc_instance = fields.Many2one('ks.woo.connector.instance', string='Instance', required=False)
    ks_export_in_wo = fields.Boolean('Exported in Woo',
                                     readonly=True,
                                     store=True,
                                     compute='_ks_compute_export_in_woo',
                                     help="""Exported in Woo: If enabled, the Woo Tax is synced with the specified 
                                        WooCommerce Instance""")

    @api.depends('ks_woo_id')
    def _ks_compute_export_in_woo(self):
        """
        This will make enable the Exported in Woo if record has the WooCommerce Id

        :return: None
        """
        for rec in self:
            rec.ks_export_in_wo = bool(rec.ks_woo_id)

class KsAccountMoveLine(models.Model):
    _inherit = "account.move.line"

    ks_discount_amount_value = fields.Float(string='Discount Amount', digits=(16, 4))

    # @api.model_create_multi
    # def create(self, vals_list):
    #     # OVERRIDE
    #     ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
    #     BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
    #
    #     for vals in vals_list:
    #         move = self.env['account.move'].browse(vals['move_id'])
    #         vals.setdefault('company_currency_id',
    #                         move.company_id.currency_id.id)  # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message
    #
    #         # Ensure balance == amount_currency in case of missing currency or same currency as the one from the
    #         # company.
    #         currency_id = vals.get('currency_id') or move.company_id.currency_id.id
    #         if currency_id == move.company_id.currency_id.id:
    #             balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
    #             vals.update({
    #                 'currency_id': currency_id,
    #                 'amount_currency': balance,
    #             })
    #         else:
    #             vals['amount_currency'] = vals.get('amount_currency', 0.0)
    #
    #         if move.is_invoice(include_receipts=True):
    #             currency = move.currency_id
    #             partner = self.env['res.partner'].browse(vals.get('partner_id'))
    #             taxes = self.new({'tax_ids': vals.get('tax_ids', [])}).tax_ids
    #             tax_ids = set(taxes.ids)
    #             taxes = self.env['account.tax'].browse(tax_ids)
    #
    #             # Ensure consistency between accounting & business fields.
    #             # As we can't express such synchronization as computed fields without cycling, we need to do it both
    #             # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
    #             # business [resp. accounting] fields are recomputed.
    #             if any(vals.get(field) for field in ACCOUNTING_FIELDS):
    #                 price_subtotal = self._get_price_total_and_subtotal_model(
    #                     vals.get('price_unit', 0.0),
    #                     vals.get('quantity', 0.0),
    #                     vals.get('discount', 0.0),
    #                     currency,
    #                     self.env['product.product'].browse(vals.get('product_id')),
    #                     partner,
    #                     taxes,
    #                     move.move_type,
    #                 ).get('price_subtotal', 0.0)
    #                 vals.update(self._get_fields_onchange_balance_model(
    #                     vals.get('quantity', 0.0),
    #                     vals.get('discount', 0.0),
    #                     vals['amount_currency'],
    #                     move.move_type,
    #                     currency,
    #                     taxes,
    #                     price_subtotal
    #                 ))
    #                 vals.update(self._get_price_total_and_subtotal_model(
    #                     vals.get('price_unit', 0.0),
    #                     vals.get('quantity', 0.0),
    #                     vals.get('discount', 0.0),
    #                     currency,
    #                     self.env['product.product'].browse(vals.get('product_id')),
    #                     partner,
    #                     taxes,
    #                     move.move_type,
    #                 ))
    #             elif any(vals.get(field) for field in BUSINESS_FIELDS):
    #                 vals.update(self._get_price_total_and_subtotal_model(
    #                     vals.get('price_unit', 0.0),
    #                     vals.get('quantity', 0.0),
    #                     vals.get('discount', 0.0),
    #                     currency,
    #                     self.env['product.product'].browse(vals.get('product_id')),
    #                     partner,
    #                     taxes,
    #                     move.move_type,
    #                 ))
    #                 vals.update(self._get_fields_onchange_subtotal_model(
    #                     vals['price_subtotal'],
    #                     move.move_type,
    #                     currency,
    #                     move.company_id,
    #                     move.date,
    #                 ))
    #     for rec in vals_list:
    #         if rec.get('tax_repartition_line_id'):
    #             ks_data = True if rec.get('credit') else False
    #             if self.env['account.move'].search([('id', '=', rec.get('move_id'))]).line_ids and self.env['account.move'].search([('id', '=', rec.get('move_id'))]).line_ids[0].sale_line_ids and self.env['account.move'].search([('id', '=', rec.get('move_id'))]).line_ids[0].sale_line_ids[0].order_id.ks_wc_instance:
    #                 if ks_data:
    #                     if self.env['account.move'].search(
    #                             [('id', '=', rec.get('move_id'))]).line_ids[0].sale_line_ids[0].order_id.ks_wc_instance.ks_invoice_tax_account:
    #                         rec.update({
    #                             'account_id': self.env['account.move'].search(
    #                                 [('id', '=', rec.get('move_id'))]).line_ids[0].sale_line_ids[0].order_id.ks_wc_instance.ks_invoice_tax_account.id
    #                         })
    #                 else:
    #                     if self.env['account.move'].search(
    #                             [('id', '=', rec.get('move_id'))]).line_ids[0].sale_line_ids[0].order_id.ks_wc_instance.ks_credit_tax_account:
    #                         rec.update({
    #                             'account_id': self.env['account.move'].search(
    #                                 [('id', '=', rec.get('move_id'))]).line_ids[0].sale_line_ids[
    #                                 0].order_id.ks_wc_instance.ks_credit_tax_account.id
    #                         })
    #             elif self.env['account.move'].search([('id', '=', rec.get('move_id'))]).ks_woo_order_id and self.env['account.move'].search([('id', '=', rec.get('move_id'))]).ks_woo_order_id.ks_wc_instance:
    #                 if ks_data:
    #                     if self.env['account.move'].search([('id', '=', rec.get('move_id'))]).ks_woo_order_id.ks_wc_instance.ks_invoice_tax_account:
    #                         rec.update({
    #                         'account_id': self.env['account.move'].search([('id', '=', rec.get(
    #                             'move_id'))]).ks_woo_order_id.ks_wc_instance.ks_invoice_tax_account.id})
    #                 else:
    #                     if self.env['account.move'].search([('id', '=',
    #                                                          rec.get('move_id'))]).ks_woo_order_id.ks_wc_instance.ks_credit_tax_account:
    #                         rec.update({
    #                             'account_id': self.env['account.move'].search([('id', '=', rec.get(
    #                                 'move_id'))]).ks_woo_order_id.ks_wc_instance.ks_credit_tax_account.id})
    #
    #     lines = super(KsAccountMoveLine, self).create(vals_list)
    #
    #     moves = lines.mapped('move_id')
    #     if self._context.get('check_move_validity', True):
    #         moves._check_balanced()
    #     moves._check_fiscalyear_lock_date()
    #     lines._check_tax_lock_date()
    #     moves._synchronize_business_models({'line_ids'})
    #     return lines