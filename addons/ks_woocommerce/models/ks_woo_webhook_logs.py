# -*- coding: utf-8 -*-

from odoo import api, fields, models

class KsWooWebhookLogs(models.Model):
    _name = "ks.woo.webhook.logger"
    # _rec_name = "ks_name"
    _order = 'create_date desc'
    _description = "Used to maintain logging of Webhook logs of woocommerce"

    name = fields.Char("Name", compute="ks_compute_name")
    # ks_log_id = fields.Char(string="Log Id", readonly=True, default=lambda self: 'New')
    ks_operation_performed = fields.Selection([('order_create', 'Order Create'),
                                               ('product_create', 'Product Create'),
                                               ('customer_create', 'Customer Create'),
                                               ('coupon_create', 'Coupon Create'),
                                               ('order_update', 'Order Update'),
                                               ('product_update', 'Product Update'),
                                               ('customer_update', 'Customer Update'),
                                               ('coupon_update', 'Coupon Update')],
                                              string="Operation Performed",
                                              help="Displays operation type which is performed")
    ks_type = fields.Selection([('webhook', 'Webhook')], string="Domain", help="Shows name of the model")
    ks_woo_instance = fields.Many2one("ks.woo.connector.instance", string="WooCommerce Instance",
                                      help="Displays WooCommerce Instance Name")
    ks_message = fields.Text(string="Logs Message", help="Displays the Summary of the Logs")
    ks_woo_id = fields.Integer(string="Woocommerce ID")
    ks_status = fields.Selection([('draft', 'Draft'), ('failed', 'Failed')], string="Operation Status",
                                 help="Displays the status of the operation Trigger/Not Trigger")
    ks_webhook_id = fields.Many2one('ks.webhooks.configuration', 'WebHook')

    def ks_compute_name(self):
        for rec in self:
            rec.name = "Webhook Logger " + str(rec.id)

    # @api.model
    # def create(self, vals):
    #     """
    #     Creates log records with auto unique sequence
    #     :param vals: creation data
    #     :return: super
    #     """
    #     seq = self.sudo().env['ir.sequence'].next_by_code('increment_webhook_log_field') or ('New')
    #     vals['ks_log_id'] = seq
    #     return super(KsWooWebhookLogs, self).create(vals)

    # def ks_assign_record_with_woo_id(self, type, ks_woo_instance, id, params):
    #     """
    #     Assigning the Woo ID to the default model in the log
    #     :param ks_woo_instance: Woo Instance
    #     :param type: Data type
    #     :param id: ID of the record
    #     :param params: parameters of the logs
    #     :return: None
    #     """
    #     if type == 'webhook' and id:
    #         ks_webhook = self.ks_webhook_id.search(
    #             [('ks_webhook_id', '=', id), ('ks_wc_instance', '=', ks_woo_instance.id)], limit=1)
    #         if ks_webhook:
    #             params.update({
    #                 'ks_webhook_id': ks_webhook.id,
    #                 'ks_name': ks_webhook.name,
    #             })
    #     return params

    def ks_create_webhook_log_param(self, ks_operation_performed, ks_type, ks_status, ks_woo_instance,ks_woo_id, ks_message, ks_error=False):
        """
        Generic method to create logs
        :param ks_operation_performed: type of operation
        :param ks_type: domain name
        :param ks_woo_instance: woocommerce instance
        :param ks_message: process conclusion message
        :param ks_operation_flow: operation flow
        :param ks_status: operation status
        :param ks_model: model id
        :param ks_layer_model: layer model id
        :param ks_error: error
        :return:
        """
        params = {
            'ks_operation_performed': ks_operation_performed,
            'ks_type': ks_type,
            'ks_woo_instance': ks_woo_instance.id if ks_woo_instance else False,
            'ks_message': ks_message if not (ks_error) else (ks_message + " " + str(ks_error)),
            'ks_status': ks_status,
            'ks_woo_id': ks_woo_id
        }
        self.create(params)
