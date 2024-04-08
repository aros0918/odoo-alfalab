import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class KsAccountTax(models.Model):
    _inherit = "account.tax"

    def ks_woo_get_all_account_tax(self, instance, include=False):
        """
        Use: This function will get all the tax from WooCommerce
           :woo_instance: woo instance
           :include : parameter to filter out records
           :return: Dictionary of Created Woo tax
           :rtype: dict
                       """
        multi_api_call = True
        per_page = 100
        page = 1
        all_retrieved_data = []
        try:
            if include:
                include = include.split(",")
                for rec in include:
                    wc_api = instance.ks_woo_api_authentication()
                    taxes_data_response = wc_api.get("taxes/%s" % rec)
                    if taxes_data_response.status_code in [200, 201]:
                        all_retrieved_data.append(taxes_data_response.json())
                    else:
                        self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                           status="failed",
                                                                           type="tax",
                                                                           operation_flow="woo_to_odoo",
                                                                           instance=instance,
                                                                           woo_id=0,
                                                                           message=str(taxes_data_response.text))
            else:
                params = {'per_page': per_page,
                          'page': page}
                while multi_api_call:
                    wc_api = instance.ks_woo_api_authentication()
                    taxes_data_response = wc_api.get("taxes", params=params)
                    if taxes_data_response.status_code in [200, 201]:
                        all_retrieved_data.extend(taxes_data_response.json())
                    else:
                        self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                                           status="failed",
                                                                           type="tax",
                                                                           operation_flow="woo_to_odoo",
                                                                           instance=instance,
                                                                           woo_id=0,
                                                                           message=str(taxes_data_response.text))
                    total_api_calls = taxes_data_response.headers._store.get('x-wp-totalpages')[1]
                    remaining_api_calls = int(total_api_calls) - page
                    if remaining_api_calls > 0:
                        page += 1
                    else:
                        multi_api_call = False
        except Exception as e:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="failed",
                                                               type="tax",
                                                               instance=instance,
                                                               operation_flow="woo_to_odoo",
                                                               woo_id=0,
                                                               message=str(e))
        else:
            self.env['ks.woo.logger'].ks_create_api_log_params(operation_performed="fetch",
                                                               status="success",
                                                               type="tax",
                                                               operation_flow="woo_to_odoo",
                                                               instance=instance,
                                                               woo_id=0,
                                                               message="Fetch of Category successful")
        return all_retrieved_data

    def ks_get_tax_ids(self, instance, data):
        """
        Creates and Updates the tax in the odoo side
        :param instance: woo instance
        :param data: the tax data from woocommerce
        :return: tax
        """
        tax_exist = self.env['account.tax']
        if data:
            tax_exist = tax_exist.search([('ks_woo_id', '=', data.get('id')),
                                                        ('ks_wc_instance', '=', instance.id)], limit=1)
            try:
                tax_value = self.env['ir.config_parameter'].sudo().get_param(
                    'account.show_line_subtotals_tax_selection')
                if tax_value == 'tax_excluded':
                    price_include = False
                elif tax_value == 'tax_included':
                    price_include = True
                else:
                    price_include = False
                ks_name = (str(data.get('country')) + '-' + str(data.get('name') + '-' + str(data.get('priority'))))
                woo_tax_data = {
                    'name': ks_name.upper(),
                    'ks_woo_id': data.get('id'),
                    'ks_wc_instance': instance.id,
                    'amount': float(data.get('rate') or 0),
                    'amount_type': 'percent',
                    'company_id': instance.ks_company_id.id,
                    'type_tax_use': 'sale',
                    'active': True,
                    'price_include': price_include,
                }
                if tax_exist:
                    tax_exist.write(woo_tax_data)
                else:
                    tax_exist = self.env['account.tax'].create(woo_tax_data)
            except Exception as e:
                self.env['ks.woo.logger'].ks_create_log_param(ks_operation_performed='create',
                                                              ks_woo_instance=instance,
                                                              ks_record_id=0,
                                                              ks_message='Create/Fetch of Taxes Failed',
                                                              ks_woo_id=0,
                                                              ks_operation_flow='woo_to_odoo',
                                                              ks_status="failed",
                                                              ks_type="system_status",
                                                              ks_error=e)
        return tax_exist
