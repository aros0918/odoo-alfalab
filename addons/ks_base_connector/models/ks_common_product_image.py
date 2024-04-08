# -*- coding: utf-8 -*-

import base64

import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class KsBaseProductImage(models.Model):
    _name = 'ks.common.product.images'
    _description = 'Common Gallery Product Images'
    _order = 'sequence, id'

    ks_name = fields.Char(string="Image Name")
    ks_variant_id = fields.Many2one('product.product', string='Product Variant', ondelete='cascade')
    ks_template_id = fields.Many2one('product.template', string='Product template', ondelete='cascade')
    ks_image = fields.Image(string='Image')
    ks_url = fields.Char(string="Image URL", help="External URL of image")
    sequence = fields.Integer(help="Sequence of images.", index=True, default=10)
    ks_profile_image = fields.Boolean(string='Profile Image or not ?')

    @api.model
    def get_image_from_url(self, url):
        """
        This will read image from the URL if found
        :param url: image url
        :return: Encoded image
        """
        all_image_types = ["image/jpeg", "image/png", "image/tiff", "image/x-icon", "image/svg+xml", "image/gif"]
        try:
            response = requests.get(url, stream=True, verify=False, timeout=10)
            if response.status_code == 200:
                if response.headers["Content-Type"] in all_image_types:
                    image = base64.b64encode(response.content)
                    if image:
                        return image
            raise UserError(_("Can't find image.Please provide valid Image URL.\n URL: %s" % url))
        except Exception:
            raise UserError(_("Can't find image.Please provide valid Image URL.\n URL: %s" % url))

    @api.model_create_multi
    def create(self, values_list):
        """
        To generate a custom URL for the images with encoding their ID
        """
        for values in values_list:
            if self.env.context.get("main_image", False):
                values.update({"ks_profile_image": True})
            if not values.get("ks_image", False) and values.get("ks_url", ""):
                # Read image from URL if a image URL is given instead of image
                image = self.get_image_from_url(values.get("ks_url"))
                values.update({"ks_image": image})
            record = super(KsBaseProductImage, self).create(values)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            rec_id = str(record.id)
            image_url = base_url + '/ks_image/%s/%s/%s' % (
                self.env.cr.dbname,
                self.env.user.id,
                rec_id)
            record.write({'ks_url': image_url})
        return record
