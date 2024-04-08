# -*- coding: utf-8 -*-

from odoo import fields, models, api


class KsBaseSaleWorkFlowConfiguration(models.Model):
    _name = 'ks.woo.auto.sale.workflow.configuration'
    _description = 'WooCommerce Auto Sale WorkFlow Configuration'

    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="WooCommerce Instance", ondelete='cascade')
    ks_sale_workflow_id = fields.Many2one("ks.sale.workflow.configuration", string="Sale Workflow", ondelete='cascade')
    ks_woo_payment_id = fields.Many2one("ks.woo.payment.gateway", string="Payment Gateway", ondelete='cascade',
                                        )
    ks_woo_order_status = fields.Many2many("ks.woo.order.status", string="Order Status")
    ks_order_import_type = fields.Selection(related='ks_wc_instance.ks_order_import_type',
                                            string="Import Orders through")

    @api.onchange('ks_sale_workflow_id')
    def ks_onchange_order_status(self):
        """
        Return the domain for ks_sale_workflow_id in terms of order status
        :return: domain
        """
        instance = False
        for rec in self:
            if self.env.context.get('instance'):
                instance = self.env['ks.woo.connector.instance'].browse(self.env.context.get('instance'))
            else:
                instance = rec.ks_wc_instance if type(
                rec.ks_wc_instance.id) == int else rec.ks_wc_instance._origin
            return {'domain': {'ks_woo_order_status': [('id', 'in', rec.ks_wc_instance.ks_order_status.ids)],
                'ks_woo_payment_id': [('id', 'in', self.env['ks.woo.payment.gateway'].search(
                    [('ks_wc_instance', '=', instance.id)]).ids)]}}
        # for rec in self:
        #     return {'domain': {'ks_woo_order_status': [('id', 'in', rec.ks_wc_instance.ks_order_status.ids)]}}


class KsWooOrderStatus(models.Model):
    _name = "ks.woo.order.status"
    _description = "Handles Order Status"
    _rec_name = "name"

    status = fields.Selection([('on-hold', "On Hold"),
                               ('processing', "Processing"),
                               ("completed", "Completed"),
                               ("pending", "Pending"),("failed","Failing")], string="Status")
    name = fields.Char(string="Status Name")
