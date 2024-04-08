# -*- coding: utf-8 -*-

import logging
import datetime

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class KsWooResPartner(models.Model):
    _name = "ks.woo.partner"
    _rec_name = "ks_res_partner"
    _description = "Custom Partner to Connect Multiple Connectors"

    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance", readonly=True,
                                     help=_("WooCommerce Connector Instance reference"),
                                     ondelete='cascade')
    ks_woo_partner_id = fields.Integer(string="Woo Customer ID", readonly=True,
                                       help=_("the record id of the customer record defined in the Connector"))
    ks_res_partner = fields.Many2one("res.partner", string="Odoo Partner", readonly=True, ondelete='cascade',
                                     help="Displays Odoo related record name")
    ks_company_id = fields.Many2one("res.company", string="Company", compute="_compute_company", store=True,
                                    help="Displays Company Name")
    ks_date_created = fields.Datetime(string="Date Created", help=_("The date on which the record is created on the "
                                                                    "Connected Connector Instance"), readonly=True)
    ks_date_updated = fields.Datetime(string="Date Updated", help=_("The latest date on which the record is updated on"
                                                                    " the Connected Connector Instance"), readonly=True)
    ks_username = fields.Char(string="Username", readonly=True)
    ks_mapped = fields.Boolean(string="Manually Mapped", readonly=True)

    ks_sync_date = fields.Datetime('Modified On', readonly=True,
                                   help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On', readonly=True)
    ks_sync_status = fields.Boolean('Sync Status', compute='sync_update', default=False)

    def sync_update(self):
        for rec in self:
            if rec.ks_last_exported_date and rec.ks_sync_date:
                ks_reduced_ks_sync_time = rec.ks_last_exported_date - datetime.timedelta(seconds=5)
                ks_increased_ks_sync_time = rec.ks_last_exported_date + datetime.timedelta(seconds=5)
                if ks_reduced_ks_sync_time < rec.ks_sync_date < ks_increased_ks_sync_time:
                    rec.ks_sync_status = True
                else:
                    rec.ks_sync_status = False
            else:
                rec.ks_sync_status = False

    @api.depends('ks_res_partner')
    def _compute_company(self):
        """
        Computes company for the res partner to be created on odoo layer
        :return:
        """
        for rec in self:
            if rec.ks_wc_instance:
                rec.ks_company_id = rec.ks_wc_instance.ks_company_id.id

    def check_if_already_prepared(self, instance, res_partner):
        """
        Checks if the record is already prepared to export
        :param instance: Woocommerce Instance
        :param res_partner: res partner domain
        :return: customer exist domain
        """
        customer_exist = self.search([('ks_wc_instance', '=', instance.id),
                                      ('ks_res_partner', '=', res_partner.id)], limit=1)
        if customer_exist:
            return customer_exist
        else:
            return False

    def create_woo_record(self, instance, res_partner, export_to_woo=False, queue_record=False):
        """
        Use: Prepare the main Record for WooCommerce Partner Layer Model with specific Instance
        :param instance: ks.woo.instance()
        :param res_partner: res.partner()
        :return: ks.woo.partner() if created.
        """
        try:
            customer_exist = self.search([('ks_wc_instance', '=', instance.id),
                                          ('ks_res_partner', '=', res_partner.id)])
            if not customer_exist:
                data = self.ks_map_prepare_data_for_layer(res_partner, instance)
                layer_customer = self.create(data)
                if export_to_woo:
                    try:
                        customer_response = layer_customer.ks_manage_woo_customer_export()
                    except Exception as e:
                        _logger.info(str(e))
                if customer_response:
                    self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                           status="success",
                                                                           type="customer",
                                                                           instance=instance,
                                                                           odoo_model="res.partner",
                                                                           layer_model="ks.woo.partner",
                                                                           id=res_partner.id,
                                                                           message="Layer preparation Success")
                else:
                    self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                           status="failed",
                                                                           type="customer",
                                                                           instance=instance,
                                                                           odoo_model="res.partner",
                                                                           layer_model="ks.woo.partner",
                                                                           id=res_partner.id,
                                                                           message="Customer Syncing failed")
                    layer_customer = False
                return layer_customer
            else:
                return customer_exist


        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()

            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_create",
                                                                   status="failed",
                                                                   type="customer",
                                                                   instance=instance,
                                                                   odoo_model="res.partner",
                                                                   layer_model="ks.woo.partner",
                                                                   id=res_partner.id,
                                                                   message=str(e))

    def update_woo_record(self, instance, res_partner, update_to_woo=False, queue_record=False):
        """
        Prepare the main Record for WooCommerce Partner Layer Model with specific Instance
        :param instance: ks.woo.instance()
        :param res_partner: res.partner()
        :return: ks.woo.partner() if created.
        """
        try:
            customer_exist = self.search([('ks_wc_instance', '=', instance.id),
                                          ('ks_res_partner', '=', res_partner.id)])
            if customer_exist:
                data = self.ks_map_prepare_data_for_layer(res_partner, instance)
                customer_exist.write(data)
                if update_to_woo:
                    try:
                        customer_exist.ks_manage_woo_customer_export()
                    except Exception as e:
                        _logger.info(str(e))
                self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                       status="success",
                                                                       type="customer",
                                                                       instance=instance,
                                                                       odoo_model="res.partner",
                                                                       layer_model="ks.woo.partner",
                                                                       id=res_partner.id,
                                                                       message="Layer preparation Success")
                return customer_exist

        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()

            self.env['ks.woo.logger'].ks_create_prepare_log_params(operation_performed="prepare_update",
                                                                   status="failed",
                                                                   type="customer",
                                                                   instance=instance,
                                                                   odoo_model="res.partner",
                                                                   layer_model="ks.woo.partner",
                                                                   id=res_partner.id,
                                                                   message=str(e))

    def ks_map_prepare_data_for_layer(self, res_partner, instance, json_data=False):
        """
        :param res_partner: res.partner()
        :param instance: ks.woo.connector.instance()
        :return: layer compatible data
        """
        data = {
            "ks_wc_instance": instance.id,
            "ks_res_partner": res_partner.id,
        }
        if json_data:
            data.update({"ks_username": json_data.get("user_name", '')})
        return data

    def create_layer_partner(self, odoo_partner, instance, json_data):
        """
        :param odoo_partner: res.partner()
        :param instance: ks.woo.connector.instance()
        :return: ks.woo.partner()
        """
        try:
            if odoo_partner and instance:
                layer_data = self.ks_map_prepare_data_for_layer(odoo_partner, instance, json_data)
                layer_partner = self.create(layer_data)
                return layer_partner

        except Exception as e:
            raise e

    def update_layer_partner(self, odoo_partner, instance, json_data):
        """
        :param odoo_partner: res.partner()
        :param instance: ks.woo.connector.instance()
        :return: ks.woo.partner()
        """
        try:
            if odoo_partner and instance:
                layer_data = self.ks_map_prepare_data_for_layer(odoo_partner, instance, json_data)
                self.write(layer_data)
                return self
        except Exception as e:
            raise e

    def ks_woo_import_customers(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance and e.ks_woo_partner_id)
                if len(records):
                    for dat in records:
                        json_data = [self.ks_woo_get_customer(dat.ks_woo_partner_id, dat.ks_wc_instance)]
                        if json_data[0]:
                            self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(data=json_data,
                                                                                             instance=dat.ks_wc_instance)
                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Customers Records enqueued in Queue 
                                                                              Please refer Queue and logs for further details
                                                                              ''')
            except Exception as e:
                raise e

        else:
            try:
                self.ensure_one()
                if self.ks_woo_partner_id and self.ks_wc_instance:
                    json_data = self.ks_woo_get_customer(self.ks_woo_partner_id, self.ks_wc_instance)
                    if json_data:
                        self.ks_manage_woo_customer_import(self.ks_wc_instance, json_data)

                return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                       "Action Performed. Please refer logs for further details.")
            except Exception as e:
                raise e

    def ks_woo_export_customers(self):
        if len(self) > 1:
            try:
                records = self.filtered(lambda e: e.ks_wc_instance)
                if len(records):
                    self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(records=records)
                    return self.env['ks.message.wizard'].ks_pop_up_message("success",
                                                                           '''Customers Records enqueued in Queue 
                                                                              Please refer Queue and logs for further details
                                                                              ''')
            except Exception as e:
                raise e
        else:
            try:
                self.ensure_one()
                if self.ks_wc_instance:
                    self.ks_manage_woo_customer_export()
                return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                                       "Action Performed. Please refer logs for further details.")
            except Exception as e:
                raise e

    def ks_manage_woo_customer_import(self, instance, partner_json, odoo_main_customer=False, queue_record=False):
        """
        :param instance: ks.woo.connector.instance()
        :param partner_json: json data for woocommerce about customer
        :param queue_record: Boolean Trigger for queue job
        :return: res.partner()
        """
        try:
            partner_exist = self.search([('ks_wc_instance', '=', instance.id),
                                         ('ks_woo_partner_id', '=', partner_json.get("id"))])
            odoo_partner = None
            if partner_exist:
                try:
                    main_partner_data = self.env['res.partner'].ks_map_odoo_partner_data_to_create(partner_json,
                                                                                                   partner_exist,
                                                                                                   instance=instance)
                    odoo_partner = partner_exist.ks_res_partner.ks_odoo_customer_update(partner_exist.ks_res_partner,
                                                                                        main_partner_data)
                    woo_partner = partner_exist.update_layer_partner(odoo_partner, instance, partner_json)
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(partner_json, woo_partner,
                                                                                     'ks_woo_partner_id')
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_odoo",
                                                                       ks_woo_id=partner_json.get("id", 0),
                                                                       ks_model="res.partner",
                                                                       ks_layer_model="ks.woo.partner",
                                                                       ks_status="success",
                                                                       ks_woo_instance=instance,
                                                                       ks_record_id=woo_partner.id,
                                                                       ks_message="Customer import update success",
                                                                       ks_type="customer",
                                                                       ks_operation_flow="woo_to_odoo")
                    partner_exist.ks_sync_date = datetime.datetime.now()
                    partner_exist.ks_last_exported_date = partner_exist.ks_sync_date
                    partner_exist.sync_update()
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                       ks_woo_id=partner_json.get("id", 0),
                                                                       ks_model="res.partner",
                                                                       ks_layer_model="ks.woo.partner",
                                                                       ks_status="failed",
                                                                       ks_woo_instance=instance,
                                                                       ks_record_id=0,
                                                                       ks_message=str(e),
                                                                       ks_type="customer",
                                                                       ks_operation_flow="woo_to_odoo")
                return odoo_partner

            else:
                try:
                    if not odoo_main_customer:
                        main_partner_data = self.env['res.partner'].ks_map_odoo_partner_data_to_create(partner_json,
                                                                                                       instance=instance)
                        odoo_partner = self.env['res.partner'].ks_odoo_customer_create(main_partner_data)
                    else:
                        main_partner_data = self.env['res.partner'].ks_map_odoo_partner_data_to_create(partner_json,
                                                                                                       instance=instance)
                        odoo_main_customer.write(main_partner_data)
                        odoo_partner = odoo_main_customer
                    woo_partner = self.create_layer_partner(odoo_partner, instance, partner_json)
                    self.env['ks.woo.connector.instance'].ks_woo_update_the_response(partner_json, woo_partner,
                                                                                     'ks_woo_partner_id')
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_odoo",
                                                                       ks_woo_id=partner_json.get("id", 0),
                                                                       ks_model="res.partner",
                                                                       ks_layer_model="ks.woo.partner",
                                                                       ks_status="success",
                                                                       ks_woo_instance=instance,
                                                                       ks_record_id=woo_partner.id,
                                                                       ks_message="Customer import create success",
                                                                       ks_type="customer",
                                                                       ks_operation_flow="woo_to_odoo")
                    woo_partner.ks_sync_date = datetime.datetime.now()
                    woo_partner.ks_last_exported_date = woo_partner.ks_sync_date
                    woo_partner.sync_update()
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                       ks_woo_id=partner_json.get("id", 0),
                                                                       ks_model="res.partner",
                                                                       ks_layer_model="ks.woo.partner",
                                                                       ks_status="failed",
                                                                       ks_woo_instance=instance,
                                                                       ks_record_id=0,
                                                                       ks_message=str(e),
                                                                       ks_type="customer",
                                                                       ks_operation_flow="woo_to_odoo")

                return odoo_partner

        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            raise e

    def ks_convert_odoo_compatible_data(self, data, type=False, instance=False):
        """
        :param data: json data for woo
        :return: odoo compatible data
        """
        country = self.env['res.partner'].ks_fetch_country(data.get('country') or False)
        state = self.env['res.partner'].ks_fetch_state(data.get('state') or False, country)
        data = {
            "name": "%s %s" % (data.get('first_name'), data.get('last_name') or '') or '',
            "street": data.get('address_1') or '',
            "street2": data.get('address_2') or '',
            "city": data.get('city') or '',
            "zip": data.get('postcode') or '',
            "state_id": state.id,
            "country_id": country.id,
            "email": data.get('email') or '',
            "phone": data.get('phone') or '',
        }
        if type == "billing":
            data.update({
                "type": 'invoice'
            })
        if type == "shipping":
            data.update({
                "type": "delivery"
            })
        if instance:
            data.update({
                "company_id": instance.ks_company_id.id
            })
        return data

    def ks_manage_woo_customer_export(self, queue_record=False):
        """
        :param queue_record: Boolean Trigger for queue jobs
        :return: partner json response
        """
        try:
            woo_customer_data_response = None
            odoo_base_partner = self.ks_res_partner
            instance = self.ks_wc_instance
            if self.ks_woo_partner_id and instance and odoo_base_partner:
                try:
                    data = odoo_base_partner.ks_prepare_data_to_export(self)
                    woo_customer_data_response = self.ks_woo_update_customer(self.ks_woo_partner_id,
                                                                             data,
                                                                             instance)
                    if woo_customer_data_response:
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(woo_customer_data_response,
                                                                                         self,
                                                                                         'ks_woo_partner_id')
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update_woo",
                                                                           ks_woo_id=woo_customer_data_response.get(
                                                                               "id", 0),
                                                                           ks_model="res.partner",
                                                                           ks_layer_model="ks.woo.partner",
                                                                           ks_status="success",
                                                                           ks_woo_instance=instance,
                                                                           ks_message="Customer Export update success",
                                                                           ks_record_id=self.ks_res_partner.id,
                                                                           ks_type="customer",
                                                                           ks_operation_flow="odoo_to_woo")
                        self.ks_sync_date = datetime.datetime.now()
                        self.ks_last_exported_date = self.ks_sync_date
                        self.sync_update()
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="update",
                                                                       ks_woo_id=0,
                                                                       ks_model="res.partner",
                                                                       ks_layer_model="ks.woo.partner",
                                                                       ks_status="failed",
                                                                       ks_woo_instance=instance,
                                                                       ks_record_id=self.ks_res_partner.id,
                                                                       ks_message=str(e),
                                                                       ks_type="customer",
                                                                       ks_operation_flow="odoo_to_woo")

            elif not self.ks_woo_partner_id and instance and odoo_base_partner:
                try:
                    data = odoo_base_partner.ks_prepare_data_to_export(self)
                    woo_customer_data_response = self.ks_woo_post_customer(data, instance)
                    if woo_customer_data_response:
                        self.env['ks.woo.connector.instance'].ks_woo_update_the_response(woo_customer_data_response,
                                                                                         self,
                                                                                         'ks_woo_partner_id',
                                                                                         )
                        self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create_woo",
                                                                           ks_woo_id=woo_customer_data_response.get(
                                                                               "id", 0),
                                                                           ks_model="res.partner",
                                                                           ks_layer_model="ks.woo.partner",
                                                                           ks_status="success",
                                                                           ks_woo_instance=instance,
                                                                           ks_record_id=self.ks_res_partner.id,
                                                                           ks_message="Customer export create success",
                                                                           ks_type="customer",
                                                                           ks_operation_flow="odoo_to_woo")
                        self.ks_sync_date = datetime.datetime.now()
                        self.ks_last_exported_date = self.ks_sync_date
                        self.sync_update()
                except Exception as e:
                    self.env['ks.woo.logger'].ks_create_odoo_log_param(ks_operation_performed="create",
                                                                       ks_woo_id=0,
                                                                       ks_model="res.partner",
                                                                       ks_layer_model="ks.woo.partner",
                                                                       ks_status="failed",
                                                                       ks_woo_instance=instance,
                                                                       ks_record_id=self.ks_res_partner.id,
                                                                       ks_message=str(e),
                                                                       ks_type="customer",
                                                                       ks_operation_flow="odoo_to_woo")

            return woo_customer_data_response

        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            raise e

    def ks_get_first_last_name(self, name):
        """
        :param name: str
        :return: str
        """
        first_name = last_name = ""
        list_name = name.split()
        if len(list_name):
            if len(list_name) == 1:
                first_name = ''.join(list_name[0])
                last_name = ""
                return first_name, last_name
            else:
                first_name = ' '.join(list_name[0:-1])
                last_name = ''.join(list_name[-1])
                return first_name, last_name
        return first_name, last_name

    def ks_prepare_export_json_data(self, customer=False, invoice=False, shipping=False):
        """
        Use: This will prepare the WooCommerce Partner Layer Model data for WooCommerce
        :return: dict of prepared data
        """
        odoo_partner = self.ks_res_partner if not customer else customer
        first_name, last_name = self.ks_get_first_last_name(odoo_partner.name)
        data = {
            "email": odoo_partner.email or '',
            "first_name": first_name,
            "last_name": last_name,
        }
        if not self.ks_res_partner.child_ids:
            address_dict = self.ks_res_partner.address_get(['invoice', 'delivery'])
        else:
            partner_id = self.ks_res_partner.ks_partner_ids.search(
                [('ks_wc_instance', '=', self.ks_wc_instance.id), ('id', '=', self.id)]).ks_res_partner
            # invoice_address_id = partner_id.child_ids.search([('type','=','invoice'), ('parent_id', '=', self.ks_res_partner.id)]).ids
            # delivery_address_id = partner_id.child_ids.search([('type','=','delivery'), ('parent_id', '=', self.ks_res_partner.id)]).ids
            # if len(invoice_address_id) != 0:
            #     invoice_address_id = max(invoice_address_id)
            # else:
            #     invoice_address_id = partner_id.id
            # if len(delivery_address_id) != 0:
            #     delivery_address_id = max(delivery_address_id)
            # else:
            #     delivery_address_id = partner_id.id
            invoice_address_id = invoice.id
            delivery_address_id = shipping.id

            address_dict = {'invoice': invoice_address_id, 'delivery': delivery_address_id}

        if address_dict.get("invoice"):
            invoice_partner = self.ks_res_partner.browse(address_dict.get("invoice"))
            first_name, last_name = self.ks_get_first_last_name(invoice_partner.name)
            billing = {
                "billing": {
                    'first_name': first_name,
                    'last_name': last_name,
                    'address_1': invoice_partner.street or '',
                    'address_2': invoice_partner.street2 or '',
                    'city': invoice_partner.city or '',
                    'state': invoice_partner.state_id.name if invoice_partner.state_id else '',
                    'country': invoice_partner.country_id.code if invoice_partner.country_id else '',
                    'postcode': invoice_partner.zip or '',
                    'email': invoice_partner.email or '',
                    'phone': invoice_partner.phone or ''

                }
            }
            data.update(billing)
        if address_dict.get("delivery"):
            delivery_partner = self.ks_res_partner.browse(address_dict.get("delivery"))
            first_name, last_name = self.ks_get_first_last_name(delivery_partner.name)
            shipping = {
                "shipping": {
                    'first_name': first_name,
                    'last_name': last_name,
                    'address_1': delivery_partner.street or '',
                    'address_2': delivery_partner.street2 or '',
                    'city': delivery_partner.city or '',
                    'state': delivery_partner.state_id.name if delivery_partner.state_id else '',
                    'country': delivery_partner.country_id.code if delivery_partner.country_id else '',
                    'postcode': delivery_partner.zip or '',
                }
            }
            data.update(shipping)
        return data

    def ks_woo_get_all_customers(self, instance,
                                 include=False):

        """
            Use: This function will get all the customers from WooCommerce API
            :param instance: ks.woo.instance() record
            :return: Dictionary of Created Woo customer
        """
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = []
        if include:
            params = {'per_page': per_page,
                      'page': page,
                      'include': include}
        else:
            params = {'per_page': per_page,
                      'page': page,
                      }
        try:
            wc_api = instance.ks_woo_api_authentication()
            while multi_api_call:
                customer_data_response = wc_api.get("customers", params=params)
                if customer_data_response.status_code in [200, 201]:
                    all_retrieved_data.extend(customer_data_response.json())
                else:
                    self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                       status="failed",
                                                                       type="customer",
                                                                       operation_flow="woo_to_odoo",
                                                                       instance=instance,
                                                                       woo_id=0,
                                                                       layer_model="ks.woo.partner",
                                                                       message=str(customer_data_response.text))
                total_api_calls = customer_data_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                    params.update({'page': page})
                else:
                    multi_api_call = False
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="customer",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance,
                                                               woo_id=0,
                                                               layer_model="ks.woo.partner",
                                                               message="Fetch of Customer successful")
            return all_retrieved_data
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="customer",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.partner",
                                                               message=str(e))

    def ks_woo_get_customer(self, customer_id, instance):
        """
         Use: Retrieve the data of any specific customer from woo to odoo
           :param customer_id: The id of customer whose data to be retrieved
           :return: Dictionary of Created Woo customer
         """
        try:
            wc_api = instance.ks_woo_api_authentication()
            customer_data_response = wc_api.get("customers/%s" % customer_id)
            if customer_data_response.status_code in [200, 201]:
                customer_data = customer_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="success",
                                                                   type="customer",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=customer_data.get("id", 0),
                                                                   layer_model="ks.woo.partner",
                                                                   message="Fetch of Customer successful")
                return customer_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                   status="failed",
                                                                   type="customer",
                                                                   operation_flow="woo_to_odoo",
                                                                   instance=instance,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.partner",
                                                                   message=str(customer_data_response.text))

        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="customer",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               layer_model="ks.woo.partner",
                                                               message=str(e))

    def ks_woo_post_customer(self, data, instance):
        """
        Use: Post the data to WooCommerce API for creating New Customers
            :param data: The json data to be created on Woo
            :param instance: ks.woo.instance() record
            :return: Dictionary of Created Woo customer
        """
        try:
            wc_api = instance.ks_woo_api_authentication()
            customer_data_response = wc_api.post("customers", data)
            if customer_data_response.status_code in [200, 201]:
                customer_data = customer_data_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create_post",
                                                                   status="success",
                                                                   type="customer",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=self.ks_res_partner.id,
                                                                   woo_id=customer_data.get("id", 0),
                                                                   layer_model="ks.woo.partner",
                                                                   message="Create of Customer successful")
                return customer_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                                   status="failed",
                                                                   type="customer",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=self.ks_res_partner.id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.partner",
                                                                   message=str(customer_data_response.text))
            raise Exception("Couldn't Connect the Instance at time of Customer Syncing !! Please check the network "
                            "connectivity or the configuration parameters are not correctly set")
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="create",
                                                               status="failed",
                                                               type="customer",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               ks_record_id=self.ks_res_partner.id,
                                                               woo_id=0,
                                                               layer_model="ks.woo.partner",
                                                               message=str(e))

    def ks_woo_update_customer(self, customer_id, data, instance):
        """
        Use: Post the data to WooCommerce API for creating New Customers
            :param customer_id: The customer woo id to be updated on woo
            :param data: The json data to be updated on Woo
            :param instance: ks.woo.instance() record
            :return: Dictionary of Updated Woo customer
                """
        try:
            wc_api = instance.ks_woo_api_authentication()
            woo_customer_response = wc_api.put("customers/%s" % customer_id, data)
            if woo_customer_response.status_code in [200, 201]:
                customer_data = woo_customer_response.json()
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update_woo",
                                                                   status="success",
                                                                   type="customer",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=self.ks_res_partner.id,
                                                                   woo_id=customer_data.get("id", 0),
                                                                   layer_model="ks.woo.partner",
                                                                   message="Update of Customer successful")
                return customer_data
            else:
                self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                                   status="failed",
                                                                   type="customer",
                                                                   operation_flow="odoo_to_woo",
                                                                   instance=instance,
                                                                   ks_record_id=self.ks_res_partner.id,
                                                                   woo_id=0,
                                                                   layer_model="ks.woo.partner",
                                                                   message=str(woo_customer_response.text))
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="update",
                                                               status="failed",
                                                               type="customer",
                                                               instance=instance,
                                                               operation_flow="odoo_to_woo",
                                                               ks_record_id=self.ks_res_partner.id,
                                                               woo_id=0,
                                                               layer_model="ks.woo.partner",
                                                               message=str(e))
