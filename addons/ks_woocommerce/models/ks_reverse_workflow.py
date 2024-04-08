from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class KsWooReverseWorkFlowConfiguration(models.Model):
    _name = 'ks.woo.reverse.workflow.configuration'
    _description = 'WooCommerce Reverse WorkFlow Configuration'

    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="WooCommerce Instance", ondelete='cascade')
    name = fields.Char(string="Name", compute='ks_compute_name', help="Reverse Workflow name")
    ks_active = fields.Boolean(string="Active", default=True)
    ks_odoo_order_status = fields.Selection([('delivery', 'Validated Delivery'),
                                             ('invoice_validated', 'Invoice Validated'), ],
                                            string="Sale Order Status", default='delivery', copy=False,
                                            help="Displays Odoo Order Status")

    def ks_compute_name(self):
        for rec in self:
            # ks_name = rec.ks_shopify_fields.capitalize() if rec.ks_auto_sync_with == 'code' else "Name"
            if rec.ks_wc_instance.display_name:
                rec.name = rec.ks_wc_instance.display_name + ' ' + 'Woo status workflow'
            else:
                rec.name = False

    @api.onchange('ks_wc_instance')
    def check_existing_workflow(self):
        if self.ks_active and self.ks_wc_instance:
            workflow_exists = self.search([('ks_wc_instance', '=', self.ks_wc_instance.id)])
            if workflow_exists:
                raise ValidationError(
                    _('The workflow the selected instance already exists!!'))

    @api.constrains('ks_wc_instance')
    def ks_workflow_cron_activation(self):
        """
        Make The Cron Active and Deactivate
        """
        for rec in self:
            if rec.ks_wc_instance and rec.ids:
                get_ids = self.search([('ks_active', '=', True), ('ks_wc_instance', '=', rec.ks_wc_instance.id),
                                       ('id', '!=', rec.ids[0])])
                if rec.ks_wc_instance and rec.ks_active:
                    rec.ks_wc_instance.ks_uwsw_cron_id.active = True
                elif not get_ids:
                    rec.ks_wc_instance.ks_uwsw_cron_id.active = False

    @api.model
    def ks_auto_update_woo_status(self, instance_id):
        """
        This function is called from the scheduler.
        This will search the sale.order() with auto_workflow_process_id and process the orders
        :return: True
        """

        orders = self.env['sale.order'].search([('ks_woo_order_id', '!=', 0), ('ks_wc_instance', '=', instance_id),
                                                ('state', 'not in', ('draft', 'sent', 'cancel'))])

        for order in orders:
            if not order.ks_woo_status == 'completed':
                workflow_config = self.search([('ks_wc_instance', '=', instance_id)])
                if workflow_config.ks_odoo_order_status == 'delivery':
                    if order.picking_ids:
                        picking_id_not_validated = order.picking_ids.filtered(
                            lambda x: x.state not in ["done", "cancel"])
                    if picking_id_not_validated:
                        _logger.info(
                            "All the devliveries for Sale Order [" + str(order.id) + "] are not validated")
                    else:
                        order.ks_woo_status = 'completed'
                        auto_update_on = self.env['ks.woo.connector.instance'].browse(
                            int(instance_id)).ks_auto_order_status_update_to_woo
                        if auto_update_on:
                            order.ks_update_status_on_woocommerce()
                elif workflow_config.ks_odoo_order_status == 'invoice_validated':
                    for order in orders:
                        if order.invoice_count > 0:
                            invoice_not_validated = order.invoice_ids.filtered(
                                lambda x: x.move_type == 'out_invoice' and x.state not in ['posted', 'cancel'])
                        if invoice_not_validated:
                            _logger.info("All the customer invoices for Sale Order [" + str(
                                order.id) + "] are not validated")
                        else:
                            order.ks_woo_status = 'completed'
                            auto_update_on = self.env['ks.woo.connector.instance'].browse(
                                int(instance_id)).ks_auto_order_status_update_to_woo
                            if auto_update_on:
                                order.ks_update_status_on_woocommerce()
        return True

class KsBaseSaleWorkFlowConfiguration(models.Model):
    _inherit = 'ks.sale.workflow.configuration'

    @api.model
    def ks_auto_process_sale_order(self):
        """
        This function is called from the scheduler.
        This will search the sale.order() with auto_workflow_process_id and process the orders
        :return: True
        """

        instance_ids = self.env["ks.woo.connector.instance"].search([('ks_instance_state', '=', 'active'), ('ks_automatic_reverse_workflow', '=', True)])
        super(KsBaseSaleWorkFlowConfiguration, self).ks_auto_process_sale_order()
        for instance in instance_ids:
            if instance.ks_automatic_reverse_workflow:
                self.env["ks.woo.reverse.workflow.configuration"].ks_auto_update_woo_status(instance.id)