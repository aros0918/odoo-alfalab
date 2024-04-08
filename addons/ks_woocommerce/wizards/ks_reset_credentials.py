import logging
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from requests.exceptions import ConnectionError

_logger = logging.getLogger(__name__)


class KsWooResetCredentials(models.TransientModel):
    _name = "ks.woo.reset.credentials"
    _description = "WooCommerce Reset Credentials"

    @api.model
    def _get_default_ks_woo_instances_ids(self):
        """
        :return: ks.woo.connector.instance() All the active WooCommerce Instances
        """
        instance_ids = self.env['ks.woo.connector.instance'].browse(self.env.context['default_ks_instances']).id
        return instance_ids

    def _get_instances_url(self):
        instance_ids = self.env['ks.woo.connector.instance'].browse(self.env.context['default_ks_instances'])
        return instance_ids.ks_store_url

    ks_instances = fields.Many2one('ks.woo.connector.instance', string="Instance", required=True,
                                   default=lambda self: self._get_default_ks_woo_instances_ids(),
                                   help="Displays WooCommerce Instance Name")
    ks_store_url = fields.Char('Store URL', required=True,
                               default=lambda self: self._get_instances_url(),
                               help="Displays the WooCommerce Store URL")
    ks_customer_key = fields.Char('Customer Key', required=True,
                                  help="Customer Key of the WooCommerce, not visible by default")
    ks_customer_secret = fields.Char('Customer Secret', required=True,
                                     help="Customer Secret of the WooCommerce, not visible by default")
    ks_verify_ssl = fields.Boolean('Verify SSL', help="Checkbox indicator for SSL Verification")

    def ks_reset_credentials(self):
        self.ks_instances.ks_instance_state = 'draft'
        old_key = self.ks_instances.ks_customer_key
        old_secret = self.ks_instances.ks_customer_secret
        self.ks_instances.write({
            'ks_customer_key':self.ks_customer_key,
            'ks_customer_secret':self.ks_customer_secret,
        })
        connect_instance = self.ks_instances.ks_woo_connect_to_instance()

        if connect_instance:
            if connect_instance.get('name') == 'Error':
                self.ks_instances.write({
                    'ks_customer_key': old_key,
                    'ks_customer_secret': old_secret,
                })
                return self.env["ks.message.wizard"].ks_pop_up_message(connect_instance.get('name'), "Credentials are Incorrect !!")
            self.ks_instances.ks_woo_activate_instance()
            return self.env["ks.message.wizard"].ks_pop_up_message("Success", "Credentials are successfully reset. Instance is now active!!")
