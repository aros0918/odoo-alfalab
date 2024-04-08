from odoo import models, fields, api

class KsResPartnerBaseInherit(models.Model):
    _inherit = "res.partner"

    def ks_odoo_customer_create(self, odoo_data):
        """
        :param odoo_data: base module compatible data
        :return: res.partner()
        """
        try:
            if odoo_data:
                odoo_customer = self.create(odoo_data)
                return odoo_customer

        except Exception as e:
            raise e

    def ks_odoo_customer_update(self, odoo_customer, odoo_data):
        """
        :param odoo_customer: res.partner()
        :param odoo_data: odoo compatible json data
        :return: res.partner()
        """
        try:
            if odoo_data and odoo_customer:
                odoo_customer.write(odoo_data)

                return odoo_customer
        except Exception as e:
            raise e


    def ks_fetch_country(self, country_code_or_name):
        """
            Search Country by code or name if not found then use =ilike operator for ignore case sensitive
            search and set limit 1 because it may be possible to find multiple country due to =ilike operator
            :param country_code_or_name: Country Code or Country Name, Type: Char
            :return: res.country()
        """
        country = self.env['res.country'].search(['|', ('code', '=ilike', country_code_or_name),
                                                  ('name', '=ilike', country_code_or_name)], limit=1)
        if not country and country_code_or_name:
            country = self.ks_create_country(country_code_or_name)
        return country

    def ks_fetch_state(self, state_code_or_name, country):
        """
            Search Country by code or name if not found then use =ilike operator for ignore case sensitive
            search and set limit 1 because it may be possible to find multiple country due to =ilike operator
            :param state_code_or_name: Country Code or Country Name, Type: Char
            :param country: res.country(): Country Record
            :return: res.country.state()
        """
        state = self.env['res.country.state'].search(['|', ('name', '=ilike', state_code_or_name),
                                                      ('code', '=ilike', state_code_or_name),
                                                      ('country_id', '=', country.id)], limit=1)
        if not state and state_code_or_name and country:
            state = self.ks_create_state(state_code_or_name, country)
        return state

    def ks_create_country(self, country_value):
        """
            Create Country if the Country is not found in the database with the Country Value
                 provided
            :param country_value: Country Name Value, Type: Char
            :return: res.country()
        """
        country = self.env['res.country'].create({'code': country_value,
                                                  'name': country_value})
        return country

    def ks_create_state(self, state_value, country):
        """
            Create State if the State is not found in the database with the State Value
                 provided in respective of the Country
            :param state_value: State Name Value, Type: Char
            :param country: res.country(): Country Record
            :return: res.country.state()
        """
        state = self.env['res.country.state'].create({'code': state_value,
                                                      'name': state_value,
                                                      'country_id': country.id})
        return state

    def ks_handle_customer_address(self, odoo_customer,data):
        """
        :param odoo_customer: res.partner()
        :param data: odoo compatible data
        :return: res.partner()
        """
        address_found = odoo_customer.child_ids.search([('parent_id', '=', odoo_customer.id),
                                                        ("name", '=ilike', data.get("name")),
                                                        ("street", '=ilike', data.get("street")),
                                                        ("street2", '=ilike', data.get("street2")),
                                                        ("city", "=ilike", data.get("city")),
                                                        ("zip", "=ilike", data.get("zip")),
                                                        ("state_id", '=', data.get("state_id")),
                                                        ("country_id", '=', data.get("country_id")),
                                                        ("email", '=ilike', data.get("email")),
                                                        ("phone", '=ilike', data.get("phone"))])
        if address_found:
            ##Run update command here
            odoo_customer.child_ids = [(4,address_found.id)]
        else:
            odoo_customer.child_ids = [(0, 0, data)]

        return odoo_customer