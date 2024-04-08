import datetime
import logging
from odoo.exceptions import ValidationError
import requests
import base64
from odoo import models, fields

_logger = logging.getLogger(__name__)


class KsResPartnerInherit(models.Model):
    _inherit = "res.partner"

    ks_partner_ids = fields.One2many("ks.woo.partner", "ks_res_partner", string="Partners")
    ks_company_id = fields.Many2one('res.company', string='KS Company', default=lambda self: self.env.company.id,
                                    required=True, readonly=True, help=" Shows the name of the company")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def ks_manage_woo_guest_customer_import(self, type, partner_json, queue_record=False, instance=False,
                                            meta_data=False):
        try:
            name = partner_json.get('first_name') + " " + partner_json.get('last_name')
            country = self.env['res.partner'].ks_fetch_country(partner_json.get('country') or False)
            state = self.env['res.partner'].ks_fetch_state(partner_json.get('state') or False, country)
            search_tuple = [
                ("name", '=ilike', name),
                ("street", '=ilike', partner_json.get("address_1")),
                ("street2", '=ilike', partner_json.get("address_2")),
                ("city", "=ilike", partner_json.get("city")),
                ("state_id", '=', state.id),
                ("zip", "=ilike", partner_json.get("postcode")),
                ("country_id", '=', country.id),
                ('type', '=', "contact")
            ]
            if instance:
                search_tuple.append(("company_id", '=', instance.ks_company_id.id))

            if type == 'billing':
                search_tuple.extend([("email", '=ilike', partner_json.get("email")),
                                     ("phone", '=ilike', partner_json.get("phone"))])
            partner_exist = self.search(search_tuple, limit=1)
            if not partner_exist:
                vals = {
                    'name': name,
                    'street': partner_json.get("address_1"),
                    'street2': partner_json.get("address_2"),
                    'city': partner_json.get("city"),
                    'state_id': state.id,
                    'zip': partner_json.get("postcode"),
                    'country_id': country.id,
                    'type': "contact",
                    'company_id': instance.ks_company_id.id if instance else self.env.company.id,
                }
                if type == 'billing':
                    vals.update({
                        'email': partner_json.get("email"),
                        'phone': partner_json.get("phone")})

                if instance and instance.ks_want_maps and meta_data:
                    customer_maps = instance.ks_meta_mapping_ids.search([('ks_wc_instance', '=', instance.id),
                                                                         ('ks_active', '=', True),
                                                                         ('ks_model_id.model', '=', 'res.partner')
                                                                         ])
                    for map in customer_maps:
                        odoo_field = map.ks_fields.name
                        json_key = map.ks_key
                        for m_data in meta_data:
                            if m_data.get('key', '') == json_key:
                                vals.update({
                                    odoo_field: m_data.get('value', '')
                                })
                partner_exist = self.create(vals)
            return partner_exist
        except Exception as e:
            if queue_record:
                queue_record.ks_update_failed_state()
            raise e

    def ks_handle_customer_address(self, odoo_customer, data, instance=False):
        """
        :param odoo_customer: res.partner()
        :param data: odoo compatible data
        :param instance: ks.woo.connector.instace()
        :return: res.partner()
    """
        domain = [('parent_id', '=', odoo_customer.id),
                  ("name", '=ilike', data.get("name")),
                  ("street", '=ilike', data.get("street")),
                  ("street2", '=ilike', data.get("street2")),
                  ("city", "=ilike", data.get("city")),
                  ("zip", "=ilike", data.get("zip")),
                  ("state_id", '=', data.get("state_id")),
                  ("country_id", '=', data.get("country_id")),
                  ("email", '=ilike', data.get("email")),
                  ("phone", '=ilike', data.get("phone"))]
        if instance:
            domain.append(('company_id', '=', instance.ks_company_id.id))
        address_found = odoo_customer.child_ids.search(domain, limit=1)
        if address_found:
            # Run update command here
            odoo_customer.child_ids = [(4, address_found.id)]
        else:
            odoo_customer.child_ids = [(0, 0, data)]

        return odoo_customer

    def action_woo_layer_customers(self):
        """
        Open action.act_window  for woo layer partner
        :return: action
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("ks_woocommerce.action_ks_woo_partner")
        action['domain'] = [('id', 'in', self.ks_partner_ids.ids)]
        return action

    def check_empty_dict(self, dictionary):
        """
        :param dictionary: json data
        :return: Boolean
        """
        for _, values in dictionary.items():
            if values:
                return False
        else:
            return True

    def ks_map_odoo_partner_data_to_create(self, json_data, odoo_partner=False, instance=False):
        """
        Maps odoo partner data to create on woo layer model
        :param json_data: api response json data format
        :return: data
        """
        data = {}
        partner_addresses = []
        billing_data = json_data.get('billing')
        shipping_data = json_data.get('shipping')
        shipping_empty = billing_empty = False
        if instance.ks_customer_company_type == True:
            if json_data.get(
                    'billing').get('company') or json_data.get('shipping').get('company'):
                data = {
                    'name': json_data.get('billing').get('company') or json_data.get('shipping').get(
                        'company'),
                    'company_type': 'company' if json_data.get('billing').get('company') or json_data.get(
                        'shipping').get(
                        'company') else 'person'
                }
            else:
                data = {
                    "name": "%s %s" % (json_data.get('first_name'), json_data.get('last_name') or '') if json_data.get(
                        'first_name') or json_data.get('last_name') else json_data.get('username'),
                    'company_type': 'company' if json_data.get('billing').get('company') or json_data.get(
                        'shipping').get(
                        'company') else 'person'
                }
        else:
            data = {
                "name": "%s %s" % (json_data.get('first_name'), json_data.get('last_name') or '') if json_data.get(
                    'first_name') or json_data.get('last_name') else json_data.get('username'),
                'company_type': 'person'
            }
            # if json_data.get('shipping').get('company'):
            #     data = ({
            #         'name': json_data.get('shipping').get('company'),
            #         'company_type': 'company'
            #     })
            # else:
            #     data = ({
            #         "name": "%s %s" % (json_data.get('first_name'), json_data.get('last_name') or '') if json_data.get(
            #             'first_name') or json_data.get('last_name') else json_data.get('username')
            #     })
        if shipping_data:
            # shipping_data.pop('company')
            shipping_empty = self.check_empty_dict(shipping_data)
        if billing_data:
            # billing_data.pop('company')
            billing_empty = self.check_empty_dict(billing_data)
        is_same_billing_address = is_same_shipping_address = False
        if odoo_partner:
            is_same_billing_address = self.ks_match_billing_address(odoo_partner, billing_data)
            is_same_shipping_address = self.ks_match_shipping_address(odoo_partner, shipping_data)
        if not shipping_empty:
            country = self.env['res.partner'].ks_fetch_country(shipping_data.get('country') or False)
            state = self.env['res.partner'].ks_fetch_state(shipping_data.get('state') or False, country)
            if not is_same_shipping_address or not odoo_partner:
                partner_addresses.append((0, 0, {
                    "name": "%s %s" % (shipping_data.get('first_name'), shipping_data.get('last_name') or '') or '',
                    "street": shipping_data.get('address_1') or '',
                    "street2": shipping_data.get('address_2') or '',
                    "city": shipping_data.get('city') or '',
                    "state_id": state.id,
                    "zip": shipping_data.get('postcode') or '',
                    "country_id": country.id,
                    "email": shipping_data.get('email') or '',
                    "phone": shipping_data.get('phone') or '',
                    "type": 'delivery',
                    'company_id': instance.ks_company_id.id if instance.ks_company_id.id else self.env.company.id
                }))
        if not billing_empty:
            country = self.env['res.partner'].ks_fetch_country(billing_data.get('country') or False)
            state = self.env['res.partner'].ks_fetch_state(billing_data.get('state') or False, country)
            if not is_same_billing_address or not odoo_partner:
                partner_addresses.append((0, 0, {
                    "name": "%s %s" % (billing_data.get('first_name'), billing_data.get('last_name') or '') or '',
                    "street": billing_data.get('address_1') or '',
                    "street2": billing_data.get('address_2') or '',
                    "city": billing_data.get('city') or '',
                    "state_id": state.id,
                    "zip": billing_data.get('postcode') or '',
                    "country_id": country.id,
                    "email": billing_data.get('email') or '',
                    "phone": billing_data.get('phone') or '',
                    "type": 'invoice',
                    'company_id': instance.ks_company_id.id if instance.ks_company_id.id else self.env.company.id
                }))
        if json_data.get('first_name') or json_data.get('last_name') or json_data.get('username'):
            if instance.ks_customer_address == 'billing':
                country = self.env['res.partner'].ks_fetch_country(billing_data.get('country') or False)
                state = self.env['res.partner'].ks_fetch_state(billing_data.get('state') or False, country)
                data.update({
                    # "name": "%s %s" % (json_data.get('first_name'), json_data.get('last_name') or '') if json_data.get(
                    #     'first_name') or json_data.get('last_name') else json_data.get('username'),
                    "street": billing_data.get('address_1') or '',
                    "street2": billing_data.get('address_2') or '',
                    "city": billing_data.get('city') or '',
                    "state_id": state.id,
                    "zip": billing_data.get('postcode') or '',
                    "country_id": country.id,
                    "email": json_data.get('email') or '',
                    "phone": billing_data.get('phone') or '',
                    "child_ids": partner_addresses,
                    'company_id': instance.ks_company_id.id if instance.ks_company_id.id else self.env.company.id
                })
            elif instance.ks_customer_address == 'shipping':
                country = self.env['res.partner'].ks_fetch_country(shipping_data.get('country') or False)
                state = self.env['res.partner'].ks_fetch_state(shipping_data.get('state') or False, country)
                data.update({
                    # "name": "%s %s" % (json_data.get('first_name'), json_data.get('last_name') or '') if json_data.get(
                    #     'first_name') or json_data.get('last_name') else json_data.get('username'),
                    "street": shipping_data.get('address_1') or '',
                    "street2": shipping_data.get('address_2') or '',
                    "city": shipping_data.get('city') or '',
                    "state_id": state.id,
                    "zip": shipping_data.get('postcode') or '',
                    "country_id": country.id,
                    "email": json_data.get('email') or '',
                    "phone": billing_data.get('phone') or '',
                    "child_ids": partner_addresses,
                    'company_id': instance.ks_company_id.id if instance.ks_company_id.id else self.env.company.id,
                })
        if instance and instance.ks_import_customer_images:
            customer_url = json_data.get('avatar_url')
            try:
                response = requests.get(customer_url, timeout=2)
                if response.ok:
                    data.update({
                        'image_1920':base64.b64encode(response.content),
                    })
            except Exception as e:
                raise e

        if instance and instance.ks_want_maps:
            customer_maps = instance.ks_meta_mapping_ids.search([('ks_wc_instance', '=', instance.id),
                                                                 ('ks_active', '=', True),
                                                                 ('ks_model_id.model', '=', 'res.partner')
                                                                 ])
            for map in customer_maps:
                odoo_field = map.ks_fields.name
                json_key = map.ks_key
                for meta_data in json_data.get("meta_data"):
                    if meta_data.get('key', '') == json_key:
                        data.update({
                            odoo_field: meta_data.get('value', '')
                        })
        return data

    def convert_billing_address(self, odoo_partner, billing_data):
        """
        :param odoo_partner: res.parner()
        :param billing_data: woo json data
        :return: Boolean Trigger True / False
        """
        odoo_raw_string = ''
        odoo_raw_string = odoo_raw_string.join([odoo_partner.name if odoo_partner.name else '',
                                                odoo_partner.street if odoo_partner.street else '',
                                                odoo_partner.street2 if odoo_partner.street2 else '',
                                                odoo_partner.city if odoo_partner.city else '',
                                                odoo_partner.zip if odoo_partner.zip else '',
                                                odoo_partner.email if odoo_partner.email else '',
                                                odoo_partner.phone if odoo_partner.phone else '']).replace(" ",
                                                                                                           "").lower()
        woo_raw_string = ''
        woo_raw_string = woo_raw_string.join([(billing_data.get("first_name", '') + billing_data.get("last_name", '')),
                                              billing_data.get('address_1', ''), billing_data.get('address_2', ''),
                                              billing_data.get('city', ''), billing_data.get('postcode', ''),
                                              billing_data.get('email', ''),
                                              billing_data.get('phone', '')
                                              ]).replace(" ", "").lower()

        return odoo_raw_string, woo_raw_string

    def convert_shipping_address(self, odoo_partner, shipping_data):
        """
        :param odoo_partner: res.partner()
        :param shipping_data: woo json shipping data
        :return: raw string
        """
        odoo_raw_string = ''
        odoo_raw_string = odoo_raw_string.join([odoo_partner.name if odoo_partner.name else '',
                                                odoo_partner.street if odoo_partner.street else '',
                                                odoo_partner.street2 if odoo_partner.street2 else '',
                                                odoo_partner.city if odoo_partner.city else '',
                                                odoo_partner.zip if odoo_partner.zip else '',
                                                odoo_partner.email if odoo_partner.email else '',
                                                odoo_partner.phone if odoo_partner.phone else '']).replace(" ",
                                                                                                           "").lower()

        woo_raw_string = ''
        woo_raw_string = woo_raw_string.join(
            [(shipping_data.get("first_name", '') + shipping_data.get("last_name", '')),
             shipping_data.get('address_1', ''), shipping_data.get('address_2', ''),
             shipping_data.get('city', ''), shipping_data.get('postcode', ''),
             shipping_data.get('email', ''),
             shipping_data.get('phone', '')
             ]).replace(" ", '').lower()
        return odoo_raw_string, woo_raw_string

    def ks_match_billing_address(self, odoo_partner, billing_data):
        """
        :param odoo_partner:res.partner()
        :param billing_data: woo json billing data
        :return: return id
        """
        billing_ids = odoo_partner.ks_res_partner.child_ids
        for id in billing_ids:
            if id.type == 'invoice':
                raw_odoo_address, raw_woo_address = self.convert_billing_address(id, billing_data)
                if raw_odoo_address == raw_woo_address:
                    return True
        return False

    def ks_match_shipping_address(self, odoo_partner, shipping_data):
        """
        :param odoo_partner:res.partner()
        :param billing_data: woo json billing data
        :return: return id
        """
        shipping_ids = odoo_partner.ks_res_partner.child_ids
        for id in shipping_ids:
            if id.type == "delivery":
                raw_odoo_address, raw_woo_address = self.convert_shipping_address(id, shipping_data)
                if raw_odoo_address == raw_woo_address and (raw_odoo_address != '' or raw_woo_address != ''):
                    return True

        return False

    def ks_get_names(self, name):
        name = name.split()
        if name:
            if len(name) == 1:
                first_name = ''.join(name[0])
                last_name = ''
                return first_name, last_name
            else:
                first_name = ''.join(name[0:-1])
                last_name = "".join(name[-1])
                return first_name, last_name
        return None, None

    def ks_prepare_data_to_export(self, layer_partner):
        """
        :param layer_partner: ks.woo.partner()
        :return: woo json data
        """
        if not self.child_ids:
            address_ids = self.address_get(['delivery', 'invoice'])
        else:
            invoice_address_id = self.child_ids.search([('type', '=', 'invoice'), ('parent_id', '=', self.id)]).ids
            delivery_address_id = self.child_ids.search([('type', '=', 'delivery'), ('parent_id', '=', self.id)]).ids
            if len(invoice_address_id) != 0:
                invoice_address_id = max(invoice_address_id)
            else:
                invoice_address_id = self.id
            if len(delivery_address_id) != 0:
                delivery_address_id = max(delivery_address_id)
            else:
                delivery_address_id = self.id

            address_ids = {'invoice': invoice_address_id, 'delivery': delivery_address_id}

        billing = self.browse(address_ids['invoice'])
        shipping = self.browse(address_ids['delivery'])
        first_name, last_name = self.ks_get_names(self.name)
        data = {
            "email": self.email or '',
            "first_name": first_name or '',
            "last_name": last_name or '',
            "user_name": layer_partner.ks_username or '',
            "billing": self.ks_manage_billing_export(billing) if billing else {},
            "shipping": self.ks_manage_shipping_export(shipping) if shipping else {}
        }
        instance = layer_partner.ks_wc_instance
        if instance and instance.ks_want_maps:
            meta = {"meta_data": []}
            customer_maps = instance.ks_meta_mapping_ids.search([('ks_wc_instance', '=', instance.id),
                                                                 ('ks_active', '=', True),
                                                                 ('ks_model_id.model', '=', 'res.partner')
                                                                 ])
            for map in customer_maps:
                json_key = map.ks_key
                odoo_field = map.ks_fields
                query = """
                    select %s from res_partner where id = %s
                """ % (odoo_field.name, layer_partner.ks_res_partner.id)
                self.env.cr.execute(query)
                results = self.env.cr.fetchall()
                if results:
                    meta['meta_data'].append({
                        "key": json_key,
                        "value": str(results[0][0])
                    })
                    data.update(meta)
        return data

    def ks_manage_billing_export(self, billing):
        """
        :param billing: res.partner() type="invoice"
        :return: billing json
        """
        if not billing.name:
            billing.name = billing.parent_id.name
        first_name, last_name = self.ks_get_names(billing.name)
        billing = {
            "first_name": first_name or '',
            "last_name": last_name or '',
            "address_1": billing.street or '',
            "address_2": billing.street2 or '',
            "city": billing.city or '',
            "state": billing.state_id.code or '',
            "postcode": billing.zip or '',
            "country": billing.country_id.code or '',
            "email": billing.email or self.email or '',
            "phone": billing.phone or billing.phone_sanitized or billing.mobile or self.phone or ''
        }
        return billing

    def ks_manage_shipping_export(self, shipping):
        """
        :param shipping:  res.partner() type="shipping"
        :return: billing json
        """
        if not shipping.name:
            shipping.name = shipping.parent_id.name
        first_name, last_name = self.ks_get_names(shipping.name)
        shipping = {
            "first_name": first_name or '',
            "last_name": last_name or '',
            "address_1": shipping.street or '',
            "address_2": shipping.street2 or '',
            "city": shipping.city or '',
            "state": shipping.state_id.code or '',
            "postcode": shipping.zip or '',
            "country": shipping.country_id.code or '',
            "phone": shipping.phone or shipping.phone_sanitized or shipping.mobile or ''
        }
        return shipping

    def ks_push_to_woocommerce(self):
        if self:
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_push').sudo().read()[0]
                action['context'] = {'push_to_woo': True}
                return action
            else:
                data_prepared = self.ks_partner_ids.filtered(lambda x: x.ks_wc_instance.id == instances.id)
                if data_prepared:
                    ##Run update woo record command here
                    self.env['ks.woo.partner'].update_woo_record(instances, self, update_to_woo=True)
                else:
                    self.env['ks.woo.partner'].create_woo_record(instances, self, export_to_woo=True)
        else:
            active_ids = self.env.context.get("active_ids")
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_push').sudo().read()[0]
                action['context'] = {'push_to_woo': True, 'active_ids': active_ids, 'active_model': 'res.partner'}
                return action
            else:
                records = self.browse(active_ids)
                if len(records) == 1:
                    data_prepared = records.ks_partner_ids.filtered(lambda x: x.ks_wc_instance.id == instances.id)
                    if data_prepared:
                        ##Run update woo record command here
                        self.env['ks.woo.partner'].update_woo_record(instances, records, update_to_woo=True)
                    else:
                        self.env['ks.woo.partner'].create_woo_record(instances, records, export_to_woo=True)
                else:
                    for rec in records:
                        data_prepared = rec.ks_partner_ids.filtered(lambda x: x.ks_wc_instance.id == instances.id)
                        if data_prepared:
                            self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instances, 'ks.woo.partner',
                                                                                            'res.partner', rec.id,
                                                                                            'update', True, True)
                        else:
                            self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instances, 'ks.woo.partner',
                                                                                            'res.partner', rec.id,
                                                                                            'create', True, True)
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_pull_from_woocommerce(self):
        if self:
            instance_counts = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instance_counts) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_pull').read()[0]
                action['context'] = {'pull_from_woo': True}
                return action
            else:
                data_prepared = self.ks_partner_ids.filtered(lambda x: x.ks_wc_instance.id == instance_counts.id)
                if data_prepared and data_prepared.ks_woo_partner_id:
                    ##Handle woo import here
                    woo_id = data_prepared.ks_woo_partner_id
                    json_data = self.env['ks.woo.partner'].ks_woo_get_customer(woo_id, instance=instance_counts)
                    if json_data:
                        partner = self.env['ks.woo.partner'].ks_manage_woo_customer_import(instance_counts, json_data)
                    else:
                        _logger.info("Fatal Error in Syncing Customer from woocommerce")

                else:
                    _logger.info("Layer record must have woo id")
        else:
            active_ids = self.env.context.get("active_ids")
            instances = self.env['ks.woo.connector.instance'].search([('ks_instance_state', 'in', ['active'])])
            if len(instances) > 1:
                action = self.env.ref('ks_woocommerce.ks_instance_selection_action_pull').read()[0]
                action['context'] = {'pull_from_woo': True, 'active_ids': active_ids, 'active_model': 'res.partner'}
                return action
            else:
                records = self.browse(active_ids)
                if len(records) == 1:
                    data_prepared = records.ks_partner_ids.filtered(lambda x: x.ks_wc_instance.id == instances.id)
                    if data_prepared and data_prepared.ks_woo_partner_id:
                        ##Handle woo import here
                        woo_id = data_prepared.ks_woo_partner_id
                        json_data = self.env['ks.woo.partner'].ks_woo_get_customer(woo_id, instance=instances)
                        if json_data:
                            partner = self.env['ks.woo.partner'].ks_manage_woo_customer_import(instances,
                                                                                               json_data)
                        else:
                            _logger.info("Fatal Error in Syncing Customer from woocommerce")
                else:
                    for rec in records:
                        data_prepared = rec.ks_partner_ids.filtered(
                            lambda x: x.ks_wc_instance.id == instances.id)
                        woo_id = data_prepared.ks_woo_partner_id
                        json_data = self.env['ks.woo.partner'].ks_woo_get_customer(woo_id, instance=instances)
                        if json_data:
                            self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance=instances,
                                                                                             data=[json_data])
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")

    def ks_manage_direct_syncing(self, record, instance_ids, push=False, pull=False):
        try:
            if len(record) == 1:
                for instance in instance_ids:
                    if push:
                        if record.company_id and record.company_id.id != instance.ks_company_id.id:
                            raise ValidationError("Customer belonging to %s, cannot be exported by %s's instance" % (
                                record.company_id.display_name, instance.ks_company_id.display_name))
                        else:
                            data_prepared = record.ks_partner_ids.filtered(lambda x: x.ks_wc_instance.id == instance.id)
                            if data_prepared:
                                ##Run update woo record command here
                                self.env['ks.woo.partner'].update_woo_record(instance, record, update_to_woo=True)
                            else:
                                self.env['ks.woo.partner'].create_woo_record(instance, record, export_to_woo=True)

                    elif pull:
                        ##Handling of pull ther records from woocommerce here
                        data_prepared = record.ks_partner_ids.filtered(lambda x: x.ks_wc_instance.id == instance.id)
                        if data_prepared and data_prepared.ks_woo_partner_id:
                            ##Handle woo import here
                            woo_id = data_prepared.ks_woo_partner_id
                            json_data = self.env['ks.woo.partner'].ks_woo_get_customer(woo_id, instance=instance)
                            if json_data:
                                partner = self.env['ks.woo.partner'].ks_manage_woo_customer_import(instance, json_data)
                            else:
                                _logger.info("Fatal Error in Syncing Customer from woocommerce")

                        else:
                            _logger.info("Layer record must have woo id")
            else:
                for instance in instance_ids:
                    if push:
                        for rec in record:
                            data_prepared = rec.ks_partner_ids.filtered(lambda x: x.ks_wc_instance.id == instance.id)
                            if data_prepared:
                                self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instance,
                                                                                                'ks.woo.partner',
                                                                                                'res.partner', rec.id,
                                                                                                'update', True, True)
                            else:
                                self.env['ks.woo.queue.jobs'].ks_create_prepare_record_in_queue(instance,
                                                                                                'ks.woo.partner',
                                                                                                'res.partner', rec.id,
                                                                                                'create', True, True)
                    elif pull:
                        for rec in record:
                            data_prepared = rec.ks_partner_ids.filtered(
                                lambda x: x.ks_wc_instance.id == instance.id)
                            woo_id = data_prepared.ks_woo_partner_id
                            json_data = self.env['ks.woo.partner'].ks_woo_get_customer(woo_id, instance=instance)
                            if json_data:
                                self.env['ks.woo.queue.jobs'].ks_create_customer_record_in_queue(instance=instance,
                                                                                                 data=[json_data])


        except Exception as e:
            raise e
            _logger.info(str(e))

    def open_mapper(self):
        """
        Open customer mapping wizard
        :return: mapped
        """
        active_records = self._context.get("active_ids", False)
        model = self.env['ir.model'].search([('model', '=', self._name)])
        mapped = self.env['ks.global.record.mapping'].action_open_mapping_wizard(model,
                                                                                 active_records,
                                                                                 "Customers Record Mapping")
        return mapped

    def write(self, values):
        for rec in self:
            ks_woo_partner = self.env['ks.woo.partner'].search([('ks_res_partner', '=', rec.id)])
            for partner in ks_woo_partner:
                if partner.ks_woo_partner_id:
                    partner.update({'ks_sync_date': datetime.datetime.now()})

        return super(KsResPartnerInherit, self).write(values)
