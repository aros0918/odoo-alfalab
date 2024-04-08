# -*- coding: utf-8 -*-

import logging
from odoo.exceptions import ValidationError
from odoo import models, fields

_logger = logging.getLogger(__name__)


class KsQueueManager(models.TransientModel):
    _name = 'ks.woo.update.product.configuration'
    _description = 'Update Woo Product Information'

    ks_wc_instance = fields.Many2many("ks.woo.connector.instance", "connector_config_rel", string="Instance ids",
                                      domain=[('ks_instance_state', '=', 'active')])
    ks_update_image = fields.Boolean("Set Image in Woo")
    ks_update_price = fields.Boolean("Set Price in Woo")
    ks_update_stock = fields.Boolean("Set Stock in Woo")
    ks_export_image_variation = fields.Boolean(string='Export Variation Images',
                                               help="Enables/disables - Variable profile image to be exported with product")
    ks_update_details = fields.Boolean("Basic Information", default=True)
    ks_update_website_status = fields.Selection([("published", "Published"),
                                                 ("unpublished", "UnPublished")], "Website Status", default="published")
    ks_woo_description = fields.Char('Description', help="Message displayed as product description on WooCommerce",
                                     translate=True)
    ks_woo_short_description = fields.Char('Short Description',
                                           help="Message displayed as product short description on WooCommerce",
                                           translate=True)

    def ks_update_product(self):
        products = self.env[self.env.context.get('active_model')].search(
            [("id", "in", self.env.context.get('active_ids'))])
        layer_product = None
        instances = self.ks_wc_instance
        if not instances:
            raise ValidationError("Choose instance before execute operation!")
        product_config = {
            "image": self.ks_update_image,
            "price": self.ks_update_price,
            "variant_image": self.ks_export_image_variation,
            "stock": self.ks_update_stock,
            "basic_info": self.ks_update_details,
            "web_status": self.ks_update_website_status,
            "server_action": True,
            "description": self.ks_woo_description,
            "short_description": self.ks_woo_short_description,
        }
        if instances:
            for instance in instances:
                for product in products:
                    if product.company_id and product.company_id.id != instance.ks_company_id.id:
                        raise ValidationError("Product belonging to %s, cannot be exported by %s's instance" % (
                            product.company_id.display_name, instance.ks_company_id.display_name))
                    else:
                        data_prepared = product.ks_product_template.filtered(
                            lambda c: c.ks_wc_instance.id == instance.id)
                        if data_prepared:
                            ##Run update prepare command and export here
                            layer_product = self.env['ks.woo.product.template'].update_woo_record(instance, product,
                                                                                                  product_config=product_config)
                        else:
                            layer_product = self.env['ks.woo.product.template'].create_woo_record(instance, product,
                                                                                                  product_config=product_config)

                    if layer_product:
                        # layer_product.ks_action_woo_export_product(product_config)
                        self.env['ks.woo.queue.jobs'].ks_create_product_record_in_queue(records=layer_product,
                                                                                        product_config=product_config)
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")
