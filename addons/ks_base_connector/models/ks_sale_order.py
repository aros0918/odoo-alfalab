# -*- coding: utf-8 -*-

from odoo import models, fields


class KsBaseSaleOrder(models.Model):
    _inherit = "sale.order"

    ks_auto_workflow_id = fields.Many2one("ks.sale.workflow.configuration", string="Auto Workflow Process", copy=False,
                                          readonly=True)

    def _prepare_invoice(self):
        """
        Override to update journal_id, date and invoice_date
        :return: Invoice values dictionary
        """
        invoice_vals = super(KsBaseSaleOrder, self)._prepare_invoice()
        if self.ks_auto_workflow_id:
            if self.ks_auto_workflow_id.ks_sale_journal_id:
                invoice_vals.update({'journal_id': self.ks_auto_workflow_id.ks_sale_journal_id.id})
            if self.ks_auto_workflow_id.ks_invoice_date_is_order_date:
                invoice_vals.update({"date": self.date_order.date(), "invoice_date": fields.Date.context_today(self)})
        return invoice_vals

    def ks_validate_order(self):
        """
        This will confirm the Order and update the actual order date to date_order field
        :return: True
        """
        self.ensure_one()
        date_order = self.date_order
        self.action_confirm()
        self.write({'date_order': date_order})
        return True

    def ks_process_order_and_invoices(self):
        """
        This will process the Order(Validate Order, invoice) according the configuration on auto workflow
        :return: True
        """
        for order in self:
            work_flow_process = order.ks_auto_workflow_id
            if order.invoice_status and order.invoice_status == 'invoiced':
                continue
            if work_flow_process.val_order and order.state in ('draft', 'sent'):
                order.ks_validate_order()
            order.ks_validate_and_paid_invoices(work_flow_process)
        return True

    def ks_validate_and_paid_invoices(self, work_flow_process):
        """
        This will validate and pay the invoices according to the workflow configuration.
        :param work_flow_process: ks.sale.workflow.configuration() object
        :return: True
        """
        self.ensure_one()
        if work_flow_process.ks_create_invoice:
            invoices = self._create_invoices()
            if work_flow_process.ks_validate_invoice:
                self.ks_validate_invoices(invoices)
            if work_flow_process.register_payment:
                self.ks_paid_invoices(invoices)
        return True

    def ks_validate_invoices(self, invoices):
        """
        This will post all the invoices
        :param invoices: account.move()
        :return: True
        """
        self.ensure_one()
        for invoice in invoices:
            invoice.action_post()
        return True

    def ks_paid_invoices(self, invoices):
        """
        This will process payment for the the posted invoices
        :param invoices: account.move()
        :return: True
        """
        self.ensure_one()
        for invoice in invoices:
            if invoice.amount_residual:
                vals = invoice.ks_prepare_payment_values(self.ks_auto_workflow_id)
                if invoice.amount_residual:
                    account_payment = self.env['account.payment'].create(vals)
                    account_payment.action_post()
                    # to reconcile the payment created
                    self.ks_reconcile_payment(account_payment, invoice)
        return True

    def ks_reconcile_payment(self, payment_id, invoice):
        """
        This will reconcile the payment posted
        :param payment_id: account.payment() object
        :param invoice: account.move() object
        :return:
        """
        move_lines = self.env['account.move.line'].search([('move_id', '=', invoice.id)])
        to_reconcile = [move_lines.filtered(lambda line: line.account_type == 'asset_receivable')]
        for payment, lines in zip([payment_id], to_reconcile):
            payment_lines = payment.line_ids.filtered_domain([
                ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('reconciled', '=', False)])
            for account in payment_lines.account_id:
                (payment_lines + lines).filtered_domain([('account_id', '=', account.id),
                                                         ('reconciled', '=', False)]).reconcile()

    def ks_confirm_delivery(self):
        """
        This will validate all the pickings for the order according to the workflow configuration
        :return: None
        """
        self.ensure_one()
        if self.ks_auto_workflow_id.ks_confirm_shipment:
            for ks_picking in self.picking_ids:
                if ks_picking.state in ('cancel', 'done'):
                    continue
                picking_id = ks_picking
                ks_counter = self.ks_product_stock_picking_done(picking_id.move_ids)
                if ks_counter == 1:
                    picking_id.button_validate()

    def ks_product_stock_picking_done(self, move_lines):
        """
        This will update the move line qty to done qty for validating the stock.picking()
        :param move_lines: stock.move() object
        :return: 0 or 1, Type: integer
        """

        ks_local_counter = 0
        for ks_move_line in move_lines:  # for validating initial == demand
            if ks_move_line.quantity_done == 0:
                ks_move_line.quantity_done = ks_move_line.product_uom_qty
                ks_local_counter += 1
        if ks_local_counter == 0:
            return 0
        else:
            return 1


