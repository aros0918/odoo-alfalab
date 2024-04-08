from odoo import api, fields, models, _
import datetime


class KsDeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    ks_woo_delivery_carrier_ids = fields.One2many('ks.woo.delivery.carrier', 'ks_delivery_carrier_id')

    def action_woo_ship_layer_templates(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("ks_woocommerce.action_ks_woo_delivery_carrier_")
        action['domain'] = [('id', 'in', self.ks_woo_delivery_carrier_ids.ids)]
        return action


class KsWooShippingMethods(models.Model):
    _name = 'ks.woo.delivery.carrier'
    _description = 'KS WOO Delivery Carrier'

    ks_title = fields.Char(string='Title')
    ks_description = fields.Char(string='Description')
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", readonly=True,
                                     help=_("WooCommerce Connector Instance reference"), ondelete='cascade')
    ks_date_created = fields.Datetime('Date Created', help=_("The date on which the record is created on the Connected"
                                                             " Connector Instance"), readonly=True)
    ks_date_updated = fields.Datetime('Date Updated', help=_("The latest date on which the record is updated on the"
                                                             " Connected Connector Instance"), readonly=True)
    ks_woo_id = fields.Char('Woo Shipping Method ID',
                            help=_("the record id of the particular record defied in the Connector"),
                            readonly=True)
    ks_delivery_carrier_id = fields.Many2one('delivery.carrier', string="Shipping Method")

    def ks_woo_get_all_shipping_methods(self, instance_id=False):
        wc_api = instance_id.ks_woo_api_authentication()
        try:
            woo_shipping_method_response = wc_api.get("shipping_methods")
            if woo_shipping_method_response.status_code in [200, 201]:
                all_retrieved_data = woo_shipping_method_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="shipping",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.delivery.carrier",
                                                                   message="Fetch of shipping_method successful")
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="shipping",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance_id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.delivery.carrier",
                                                                   message=str(woo_shipping_method_response.text))
            return all_retrieved_data
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="shipping",
                                                               instance=instance_id,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.delivery.carrier",
                                                               message=str(e))

    def ks_woo_import_shipping_method(self, shipping_method_data, instance, queue_record=False):
        shipping_record_exist = self.env['ks.woo.delivery.carrier'].search(
            [('ks_wc_instance', '=', instance.id),
             ('ks_woo_id', '=', shipping_method_data.get('id'))])
        if shipping_record_exist:
            data = self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                               ks_model='delivery.carrier',
                                                               ks_layer_model='ks.woo.delivery.carrier',
                                                               ks_message="Shipping method already synced for woo id " + shipping_method_data.get("id", str(0)),
                                                               ks_status="failed",
                                                               ks_type="shipping",
                                                               ks_record_id=0,
                                                               ks_operation_flow="woo_to_odoo",
                                                               ks_woo_id=0,
                                                               ks_woo_instance=instance)
        else:
            try:
                shipping_json_data = self.ks_prepare_import_json_data(shipping_method_data)
                if shipping_json_data:
                    carrier_record = self.env['delivery.carrier'].create(shipping_json_data)
                    woo_json_data = self.ks_prepare_import_woo_data(shipping_json_data, instance, carrier_record)
                    woo_carrier_record = self.create(woo_json_data)
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(shipping_method_data,
                                                                                     woo_carrier_record,
                                                                                     'ks_woo_id')
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                       ks_model='delivery.carrier',
                                                                       ks_layer_model='ks.woo.delivery.carrier',
                                                                       ks_message="Shipping method import create success",
                                                                       ks_status="success",
                                                                       ks_type="shipping",
                                                                       ks_record_id=carrier_record.id,
                                                                       ks_operation_flow="woo_to_odoo",
                                                                       ks_woo_id=0,
                                                                       ks_woo_instance=instance)
                    # carrier_record.ks_sync_date = datetime.datetime.now()
                    # carrier_record.ks_last_exported_date = carrier_record.ks_sync_date
                    # carrier_record.sync_update()

                    return carrier_record
            except Exception as e:
                if queue_record:
                    queue_record.ks_update_failed_state()
                self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                   ks_model='delivery.carrier',
                                                                   ks_layer_model='ks.woo.delivery.carrier',
                                                                   ks_message=str(e) + shipping_method_data.get("id", str(0)),
                                                                   ks_status="failed",
                                                                   ks_type="shipping",
                                                                   ks_record_id=0,
                                                                   ks_operation_flow="woo_to_odoo",
                                                                   ks_woo_instance=instance,
                                                                   ks_woo_id=0)

    def ks_prepare_import_json_data(self, shipping_data):
        data = {
            'name': shipping_data.get('id'),
            'delivery_type': 'fixed',
            'product_id': self.env['product.product'].search([('default_code', '=', 'Delivery_007')], limit=1).id,
        }
        return data

    def ks_prepare_import_woo_data(self, shipping_data, instance, carrier):
        data = {
            'ks_title': shipping_data.get('title'),
            'ks_description': shipping_data.get('description'),
            'ks_wc_instance': instance.id,
            'ks_woo_id': shipping_data.get('id'),
            'ks_delivery_carrier_id': carrier.id,
            'ks_date_created': datetime.datetime.now(),
            'ks_date_updated': datetime.datetime.now(),
        }
        return data
