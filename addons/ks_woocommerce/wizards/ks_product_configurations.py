import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class KsQueueManager(models.TransientModel):
    _name = 'ks.woo.product.configuration'
    _description = 'Woo Product Configurations Sync'

    ks_update_image = fields.Boolean("Set Image in Woo")
    ks_update_price = fields.Boolean("Set Price in Woo")
    ks_update_stock = fields.Boolean("Set Stock in Woo")
    ks_export_image_variation = fields.Boolean(string='Export Variation Images',
                                               help="Enables/disables - Variable profile image to be exported with product")
    ks_update_details = fields.Boolean("Basic Information", default=True)
    ks_update_website_status = fields.Selection([("published", "Published"),
                                                 ("unpublished", "UnPublished")], "Website Status", default="published")

    def ks_update_product(self):
        products = self.env[self.env.context.get('active_model')].search([("id", "in", self.env.context.get('active_ids'))])
        product_config = {
            "image": self.ks_update_image,
            "price": self.ks_update_price,
            "variant_image": self.ks_export_image_variation,
            "stock": self.ks_update_stock,
            "basic_info": self.ks_update_details,
            "web_status": self.ks_update_website_status,
            "server_action": True
        }
        products.ks_action_woo_export_product(product_config)
        return self.env["ks.message.wizard"].ks_pop_up_message("success",
                                                               "Action Performed. Please refer logs for further details.")