# -*- coding: utf-8 -*-

from odoo import models, fields


class KsWooPaymentGateway(models.Model):
    _name = 'ks.woo.payment.gateway'
    _description = 'WooCommerce Payment Gateway'
    _rec_name = 'ks_title'

    ks_title = fields.Char('Title', readonly=True, help="Displays Payment Gateway Name")
    ks_woo_pg_id = fields.Char('Payment code', readonly=True, help="Displays Payment Gateway code")
    ks_description = fields.Text(string='Description', readonly=True)
    ks_wc_instance = fields.Many2one('ks.woo.connector.instance', string='Instance', readonly=True, help="Displays WooCommerce Instance Name")
    ks_company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,
                                    required=True, readonly=True, help=" Shows the name of the company")

    def ks_map_payment_gateway_data_to_create(self, instance_id, record):
        """
        Map payment gateway json data for odoo model
        :param instance_id: Woocommerce Instance
        :param record: api response json data
        :return: odoo compatible data
        """
        data = {
            'ks_title': record.get('title') or '',
            'ks_woo_pg_id': record.get('id') or '',
            'ks_wc_instance': instance_id.id,
            'ks_description': record.get('description') or '',
        }
        return data

    def ks_prepare_import_json_data(self, pg_json_data):
        """
        prepares data to be imported on odoo
        :param pg_json_data: json data response
        :return: data for odoo model
        """
        data = {
            'ks_title': pg_json_data.get('title') or '',
            'ks_woo_pg_id': pg_json_data.get('id') or '',
            'ks_description': pg_json_data.get('description') or ''
        }
        return data

    def create_woo_record(self, instance, pg_json_data):
        """
        Creates woo data in odoo model record
        :param instance:
        :param pg_json_data: json_data
        :return: woo_pg domain response
        """
        data = self.ks_map_payment_gateway_data_to_create(instance, pg_json_data)
        try:
            woo_pg = self.create(data)
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create_woo',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=woo_pg.id,
                                                               ks_message='Create of Payment Gateway [%s] Success' % pg_json_data.get(
                                                                   "id") or "",
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="success",
                                                               ks_type="payment_gateway")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='Create of Payment Gateway [%s] on model Failed due to ' % pg_json_data.get(
                                                                   "id") or "" + str(e),
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed",
                                                               ks_type="payment_gateway")
        else:
            return woo_pg

    def ks_woo_get_all_payment_gateway(self, instance):
        """
        Gets all the payment gateway from woocommerce api
        :param instance: woocommerce instance
        :return: json data response
        """
        all_retrieved_data = []
        if instance.ks_version == 'wc/v1':
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='fetch',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='Payment Gateway api not supported by current instance',
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed",
                                                               ks_type="payment_gateway")
        else:
            try:
                wc_api = instance.ks_woo_api_authentication()
                pg_data_response = wc_api.get("payment_gateways")
                if pg_data_response.status_code in [200, 201]:
                    all_retrieved_data = pg_data_response.json()
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="payment_gateway",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.payment.gateway",
                                                                       message=str(pg_data_response.text))
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="payment_gateway",
                                                                   instance=instance,
                                                                   operation_flow="woo_to_odoo",
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.payment.gateway",
                                                                   message=str(e))
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="payment_gateway",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.payment.gateway",
                                                                   message="Fetch of Payment Gateway successful")
                return all_retrieved_data

    def ks_woo_get_payment_gateway(self, pg_id, instance):
        """
        Get payment gateway per woo id
        :param pg_id: id for woo payment gateway
        :param instance: woocommerce instance
        :return: json data response
        """
        if instance.ks_version == 'wc/v1':
            self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='fetch',
                                                          ks_woo_instance=instance,
                                                          ks_record_id=0,
                                                          ks_message='Payment Gateway api not supported by current instance',
                                                          ks_woo_id=0,
                                                          ks_operation_flow='woo_to_odoo',
                                                          ks_status="failed",
                                                          ks_type="payment_gateway")
        else:
            try:
                wc_api = instance.ks_woo_api_authentication()
                pg_data_response = wc_api.get("payment_gateways/%s" % pg_id)
                pg_data = False
                if pg_data_response.status_code in [200, 201]:
                    pg_data = pg_data_response.json()
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="success",
                                                                       type="payment_gateway",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.payment.gateway",
                                                                       message="Fetch of Payment Gateway successful")
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="payment_gateway",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.payment.gateway",
                                                                       message=str(pg_data_response.text))
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="payment_gateway",
                                                                   instance=instance,
                                                                   operation_flow="woo_to_odoo",
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.payment.gateway",
                                                                   message=str(e))
            else:
                return pg_data

    def ks_manage_woo_pg_import(self, instance, pg_json_data, queue_record=False):
        """
        Import payment gateway data from woo to odoo
        :param instance: woocommerce instance
        :param pg_json_data: api json data response
        :param queue_record: reference for queue record
        :return: created domain
        """
        try:
            pg_exist = self.env['ks.woo.payment.gateway'].search([
                ('ks_wc_instance', '=', instance.id),
                ('ks_woo_pg_id', '=', pg_json_data.get("id") or '')])
            if not pg_exist:
                woo_pg = self.create_woo_record(instance, pg_json_data)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(pg_json_data, woo_pg,
                                                                                 'ks_woo_pg_id')
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create_odoo',
                                                                   ks_woo_instance=instance,
                                                                   ks_record_id=woo_pg.id,
                                                                   ks_message="Create of payment gateway success",
                                                                   ks_woo_id=0,
                                                                   ks_operation_flow='woo_to_odoo',
                                                                   ks_status="success",
                                                                   ks_type="payment_gateway",
                                                                   ks_model='ks.woo.payment.gateway',
                                                                   ks_layer_model='ks.woo.payment.gateway')
                return woo_pg
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='create',
                                                               ks_woo_instance=instance,
                                                               ks_record_id=0,
                                                               ks_message='create of Payment Gateway [%s] Failed due to ' % pg_json_data.get(
                                                                   "id") or "" + str(e),
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed",
                                                               ks_type="payment_gateway",
                                                               ks_model='ks.woo.payment.gateway',
                                                               ks_layer_model='ks.woo.payment.gateway')

    def ks_woo_import_pg_update(self, pg_json_data, queue_record=False):
        """
        Imported data are updated if exist on odoo side in this method
        :param pg_json_data: api response json data
        :param queue_record: queue reference record
        """
        try:
            json_data = self.ks_prepare_import_json_data(pg_json_data)
            if json_data:
                self.write(json_data)
                self.env['ks.woo.connector.instance'].ks_woo_update_the_response(pg_json_data, self,
                                                                                 'ks_woo_pg_id')
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='update_odoo',
                                                                   ks_woo_instance=self.ks_wc_instance,
                                                                   ks_record_id=queue_record.ks_record_id if queue_record else self.id,
                                                                   ks_message='Update of Payment Gateway [%s] Success' % pg_json_data.get(
                                                                       "id") or "",
                                                                   ks_woo_id=0,
                                                                   ks_operation_flow='woo_to_odoo',
                                                                   ks_status="success",
                                                                   ks_type="payment_gateway",
                                                                   ks_model='ks.woo.payment.gateway',
                                                                   ks_layer_model='ks.woo.payment.gateway'
                                                                   )
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed='update',
                                                               ks_woo_instance=self.ks_wc_instance,
                                                               ks_record_id=queue_record.ks_record_id if queue_record else self.id,
                                                               ks_message='Update of Payment Gateway Failed due to ''' + str(
                                                                   e),
                                                               ks_woo_id=0,
                                                               ks_operation_flow='woo_to_odoo',
                                                               ks_status="failed",
                                                               ks_type="payment_gateway")

    def ks_woo_import_payment_gateway(self):
        """
        Action server method to import new payment gateway
        """
        pg_with_woo_id = self.filtered(lambda e: e.ks_woo_pg_id and e.ks_wc_instance)
        if len(pg_with_woo_id) > 1:
            try:
                for rec in pg_with_woo_id:
                    pg_data_response = self.ks_woo_get_payment_gateway(rec.ks_woo_pg_id, rec.ks_wc_instance)
                    if pg_data_response:
                        self.env['ks.woo.queue.jobs'].ks_create_pg_record_in_queue(rec.ks_wc_instance,
                                                                                   data=[pg_data_response])
                    else:
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                           ks_model='ks.woo.payment.gateway',
                                                                           ks_layer_model='ks.woo.payment.gateway',
                                                                           ks_message="Payment Gateway update failed",
                                                                           ks_status="failed",
                                                                           ks_type="payment_gateway",
                                                                           ks_record_id=self.id,
                                                                           ks_operation_flow="woo_to_odoo",
                                                                           ks_woo_id=0,
                                                                           ks_woo_instance=self.ks_wc_instance)
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                   ks_model='ks.woo.payment.gateway',
                                                                   ks_layer_model='ks.woo.payment.gateway',
                                                                   ks_message=str(e),
                                                                   ks_status="failed",
                                                                   ks_type="payment_gateway",
                                                                   ks_record_id=self.id,
                                                                   ks_operation_flow="woo_to_odoo",
                                                                   ks_woo_id=0,
                                                                   ks_woo_instance=self.ks_wc_instance)
            else:
                return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                       '''Payment Gateway Records enqueued in Queue 
                                                                       Please refer Queue and logs for further details
                                                                       ''')

        else:
            self.ensure_one()
            pg_data_response = self.ks_woo_get_payment_gateway(pg_with_woo_id.ks_woo_pg_id,
                                                               pg_with_woo_id.ks_wc_instance)
            self.ks_woo_import_pg_update(pg_data_response)
            return self.env['ks.message.wizard'].ks_pop_up_message("Done",
                                                                   '''Operation performed, Please refer Logs and Queues for 
                                                                   further Details.''')
