from odoo.exceptions import UserError, ValidationError
from odoo import fields, models, api,_
import logging
_logger = logging.getLogger(__name__)


class KsAutoCustomerSyncConfiguration(models.Model):
    _name = 'ks.woo.auto.customer.syncing.configuration'
    _description = 'Woo Auto Customer Syncing Configuration'

    name = fields.Char('Name', compute='ks_compute_name')
    ks_woo_instance_id = fields.Many2one("ks.woo.connector.instance", string="Woo Instance", ondelete='cascade', required=True)
    ks_customer_auto_syncing = fields.Boolean(string="Customer Auto Sync", default=False)
    # ks_auto_sync_with = fields.Selection([('name', 'Customer Name'), ('code', 'Customer Code')], string="Sync With", default=False)

    ks_woo_fields = fields.Selection([('email', 'Email ID'), ('phone', ' Phone')], string="Woo Field")
    ks_odoo_field = fields.Many2one('ir.model.fields', 'Odoo Field',
                                          domain="[('model_id', 'in', 'res.partner')]")

    ks_company_id = fields.Many2one("res.company", string="Company", compute="_compute_company", store=True,
                                    help="Displays Company Name")

    def ks_compute_name(self):
        for rec in self:
            ks_name = rec.ks_woo_fields.capitalize() if rec.ks_woo_fields == 'email' else "Phone"
            if ks_name and rec.ks_woo_instance_id.display_name:
                rec.name = rec.ks_woo_instance_id.display_name + ' ' + 'Auto Sync with' + ' ' + ks_name
            else:
                rec.name = False

    @api.depends('ks_woo_instance_id')
    def _compute_company(self):
        """
        Computes company for the woo Auto Customer Syncing Configuration
        :return:
        """
        for rec in self:
            if rec.ks_woo_instance_id.ks_company_id:
                rec.ks_company_id = rec.ks_woo_instance_id.ks_company_id.id
            else:
                rec.ks_company_id = self._context.get('company_id', self.env.company.id)

    @api.constrains('ks_customer_auto_syncing', 'ks_woo_instance_id')
    @api.onchange('ks_customer_auto_syncing', 'ks_woo_instance_id')
    def ks_check_auto_conf_active(self):
        get_ids = self.env['ks.woo.auto.customer.syncing.configuration'].search([('ks_customer_auto_syncing', '=', True)])
        for rec in self:
            if rec.ks_woo_instance_id and rec.ks_customer_auto_syncing:
                auto_sync_conf = get_ids.filtered(
                    lambda x: x.ks_woo_instance_id.id == rec.ks_woo_instance_id.id and x.id != rec.id)
                if len(auto_sync_conf) >= 1:
                    raise ValidationError(
                        _('To activate this configuration active, deselect the previously chosen configurations'
                          ' for instance %s.' % rec.ks_woo_instance_id.display_name))

    @api.constrains('ks_customer_auto_syncing', 'ks_woo_instance_id')
    def ks_onchange_ks_customer_auto_syncing(self):
        """
        Make The Cron Active and Deactivate
        """
        for rec in self:
            if rec.ks_woo_instance_id and rec.ids:
                get_ids = self.env['ks.woo.auto.customer.syncing.configuration'].search(
                    [('ks_customer_auto_syncing', '=', True), ('ks_woo_instance_id', '=', rec.ks_woo_instance_id.id),
                     ('id', '!=', rec.ids[0])])
                if rec.ks_woo_instance_id and rec.ks_customer_auto_syncing:
                    rec.ks_woo_instance_id.ks_acs_cron_id.active = True
                elif not get_ids:
                    rec.ks_woo_instance_id.ks_acs_cron_id.active = False

    def ks_auto_customer_syncing(self, cron_id=False):
        """
        Map the customers which is exist on odoo and woo.
        :param cron_id:
        :return:
        """
        try:
            self = self.with_context(auto_sync_map=True)
            if not cron_id:
                if self._context.get('params'):
                    cron_id = self.env["ir.cron"].browse(self._context.get('params').get('id'))
            else:
                cron_id = self.env["ir.cron"].browse(cron_id)
            instance_id = cron_id.ks_wc_instance
            if instance_id and instance_id.ks_instance_state == 'active':
                all_customer_data_from_woo = self.env['ks.woo.partner'].ks_woo_get_all_customers(
                    instance=instance_id)
                auto_sync_conf_rec = self.env['ks.woo.auto.customer.syncing.configuration'].search(
                    [('ks_woo_instance_id', '=', instance_id.id),
                     ('ks_customer_auto_syncing', '=', True)])
                not_sync_customers = []
                already_sync_customers = []
                if auto_sync_conf_rec and all_customer_data_from_woo:
                    for customer_json_data in all_customer_data_from_woo:
                        woo_layer_customer = self.env['ks.woo.partner'].search(
                            [('ks_woo_partner_id', '=', customer_json_data.get('id')),
                             ('ks_wc_instance', '=', instance_id.id)])
                        if not woo_layer_customer:
                            woo_layer_customer = self.ks_map_woo_customer_to_odoo_customer(instance_id,
                                                                                        auto_sync_conf_rec=auto_sync_conf_rec,
                                                                                        customer_json_data=customer_json_data)
                            if not woo_layer_customer:
                                not_sync_customers.append(customer_json_data.get('id'))
                        else:
                            already_sync_customers.append(customer_json_data.get('id'))
                if already_sync_customers:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="map_customer",
                                                                       ks_model='res.partner',
                                                                       ks_layer_model='ks.woo.partner',
                                                                       ks_message="customers %s Already Sync." % already_sync_customers,
                                                                       ks_status="failed",
                                                                       ks_type="customer",
                                                                       ks_record_id=0,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=instance_id)
                if not_sync_customers:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="map_customer",
                                                                       ks_model='res.partner',
                                                                       ks_layer_model='ks.woo.partner',
                                                                       ks_message="customers %s incompatible/not found to Sync" % not_sync_customers,
                                                                       ks_status="failed",
                                                                       ks_type="customer",
                                                                       ks_record_id=0,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=instance_id)
        except Exception as e:
            _logger.info(str(e))
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="map_customer",
                                                               ks_model='res.partner',
                                                               ks_layer_model='ks.woo.partner',
                                                               ks_message=str(e),
                                                               ks_status="failed",
                                                               ks_type="customer",
                                                               ks_record_id=0,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=0,
                                                               ks_woo_instance=instance_id)

    def ks_map_woo_customer_to_odoo_customer(self, instance_id, auto_sync_conf_rec=False,
                                           customer_json_data=False):
        odoo_main_customer = False
        woo_layer_customer = False
        # if auto_sync_conf_rec.ks_auto_sync_with == 'code':
        if customer_json_data.get(auto_sync_conf_rec.ks_woo_fields):
            odoo_main_customer = self.env['res.partner'].search([(
                auto_sync_conf_rec.ks_odoo_field.name,
                '=', customer_json_data.get(
                    auto_sync_conf_rec.ks_woo_fields))], limit=1)
            # odoo_main_customer = odoo_customer.ks_res_partner if odoo_customer else False
        if odoo_main_customer:
            woo_layer_customer = self.env['ks.woo.partner'].ks_manage_woo_customer_import(
                instance=instance_id, partner_json=customer_json_data,
                odoo_main_customer=odoo_main_customer)

            if woo_layer_customer:
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="map_customer",
                                                                   ks_model='res.partner',
                                                                   ks_layer_model='ks.woo.partner',
                                                                   ks_message="customer auto sync success",
                                                                   ks_status="success",
                                                                   ks_type="customer",
                                                                   ks_record_id=woo_layer_customer.id,
                                                                   ks_operation_flow="woo_to_odoo",
                                                                   ks_woo_id=customer_json_data.get(
                                                                       "id", 0),
                                                                   ks_woo_instance=instance_id)
        return woo_layer_customer
