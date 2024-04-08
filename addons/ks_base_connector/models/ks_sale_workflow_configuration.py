# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class KsBaseSaleWorkFlowConfiguration(models.Model):
    _name = 'ks.sale.workflow.configuration'
    _description = 'Sale WorkFlow Configuration'
    _rec_name = 'name'

    @api.model
    def _ks_get_default_journal(self):
        """
        this will get the default Journal Id
        :return: account.journal() object
        """
        company_id = self._context.get('company_id', self.env.company.id)
        domain = [('type', '=', "sale"), ('company_id', '=', company_id)]
        return self.env['account.journal'].search(domain, limit=1)

    name = fields.Char(string="Name", help="Sale Auto-Workflow name")
    val_order = fields.Boolean(string="Validate Order", help="If enabled, validates the Sale order on the basis of given conditions")
    ks_create_invoice = fields.Boolean(string='Create Invoice', help="If enabled, creates invoice for the Order on the basis of given conditions")
    ks_validate_invoice = fields.Boolean(string='Validate Invoice', help="If enabled, validates invoice for the Order on the basis of given conditions")
    ks_confirm_shipment = fields.Boolean(string='Confirm Shipment', help="If enabled, confirms shipment for the order")
    register_payment = fields.Boolean(string="Register Payment", help="If enabled, auto register payment for the order")
    ks_journal_id = fields.Many2one('account.journal', string='Payment Journal',
                                    domain=[('type', 'in', ['cash', 'bank'])], help="Displays the payment journals")
    ks_sale_journal_id = fields.Many2one('account.journal', string='Sales Journal',
                                         default=_ks_get_default_journal,
                                         domain=[('type', '=', 'sale')], help="Displays odoo sales journal")
    ks_invoice_date_is_order_date = fields.Boolean(string='Force Invoice Date', help="If it's checked, then the "
                                                                                     "invoice date will be the same as "
                                                                                     "the order date")
    ks_inbound_payment_method_id = fields.Many2one('account.payment.method', string="Debit Method",
                                                   domain=[('payment_type', '=', 'inbound')],
                                                   help="Means of payment for collecting money. Odoo modules offer various"
                                                        "payments handling facilities, but you can always use the 'Manual'"
                                                        "payment method in order to manage payments outside of the"
                                                        "software.")

    @api.model
    def ks_auto_process_sale_order(self):
        """
        This function is called from the scheduler.
        This will search the sale.order() with auto_workflow_process_id and process the orders
        :return: True
        """

        orders = self.env['sale.order'].search([('ks_auto_workflow_id', '!=', False),
                                                ('state', 'not in', ('sale', 'done', 'cancel'))])
        self.ks_process_orders(orders)
        return True

    def ks_process_orders(self, orders):
        """
        This will process the sale.order() records on the basis of WorkFlow configuration.
        :param orders: sale.order()
        :return: True
        """
        for order in orders:
            try:
                work_flow_process_record = order.ks_auto_workflow_id

                if order.invoice_status and order.invoice_status == 'invoiced':
                    continue
                order.order_line.mapped('product_id').write({
                    'invoice_policy': 'order'
                })
                if work_flow_process_record.val_order and order.state not in ('sale', 'done', 'cancel'):
                    order.ks_validate_order()
                order.ks_confirm_delivery()
                order.ks_process_order_and_invoices()
            except Exception as e:
                _logger.info("Order Processed Failed for Order [%s - %s]due to: %s" % (order.name, order.id, str(e)))
        return True
