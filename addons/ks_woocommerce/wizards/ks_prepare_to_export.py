# -*- coding: utf-8 -*-

import logging
from datetime import datetime

from odoo import fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class KsWooPrepareToExport(models.TransientModel):
    _name = 'ks.woo.prepare.to.export'
    _description = 'Prepare Records to Export the Records'

    ks_instance = fields.Many2many('ks.woo.connector.instance', string="Instance", required=True,
                                   help=_("Connector Instance reference"),
                                   domain="[('ks_instance_state', '=', 'active')]")

    def ks_prepare_record_to_export(self):
        for instance in self.ks_instance:
            active_model = self.env.context.get('active_model')
            instance_model = self.env.context.get('active_woo_model')
            active_record_ids = self.env.context.get('active_ids')
            for record_id in active_record_ids:
                current_record = self.env[active_model].browse(record_id)
                is_already_exported = self.env[instance_model].check_if_already_prepared(instance, current_record)
                if is_already_exported:
                    raise ValidationError(_('The selected record is already prepared to Export '
                                            'with the selected Instance!'))
                else:
                    export_to_woo = self.env.context.get('export_to_woo')
                    self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instance, instance_model,
                                                                                    active_model,
                                                                                    record_id, "create",
                                                                                    export_to_woo=export_to_woo)
        cron_record = self.env.ref('ks_woocommerce.ks_ir_cron_job_process')
        if cron_record:
            next_exc_time = datetime.now()
            cron_record.sudo().write({'nextcall': next_exc_time, 'active': True})
        return self.env['ks.message.wizard'].ks_pop_up_message(names='success',
                                                               message="Records has been added in queue to process!!")

    def ks_update_record_to_export(self):
        for instance in self.ks_instance:
            active_model = self.env.context.get('active_model')
            instance_model = self.env.context.get('active_woo_model')
            active_record_ids = self.env.context.get('active_ids')
            for record_id in active_record_ids:
                current_record = self.env[active_model].browse(record_id)
                is_already_exported = self.env[instance_model].check_if_already_prepared(instance, current_record)
                if not is_already_exported:
                    raise ValidationError(_('The selected record is not prepared to Update '
                                            'with the selected Instance!'))
                update_to_woo = self.env.context.get('update_to_woo')
                self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instance, instance_model
                                                                                , active_model, record_id, "update",
                                                                                update_to_woo=update_to_woo)
        cron_record = self.env.ref('ks_woocommerce.ks_ir_cron_job_process')
        if cron_record:
            next_exc_time = datetime.now()
            cron_record.sudo().write({'nextcall': next_exc_time, 'active': True})
        return self.env['ks.message.wizard'].ks_pop_up_message(names='success',
                                                               message="Records has been added in queue to process!!")

    def ks_export_customers_to_instance(self):
        active_record_ids = self.env.context.get('active_ids')
        active_model = self.env.context.get('active_model')
        for record_id in active_record_ids:
            current_record = self.env[active_model].browse(record_id)
            current_record.export_customers(self.ks_instance)

    def update_data_with_instance(self, instance_model, instance, current_record):
        self.env[instance_model].create_data_with_instance(instance, current_record)
