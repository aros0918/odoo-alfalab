# -*- coding: utf-8 -*-

from odoo import models, fields, api


class KsWooProductImage(models.Model):
    _name = 'ks.woo.product.images'
    _description = 'Woo Gallery Product Images'
    _order = 'sequence, id'

    ks_name = fields.Char("Name")
    ks_wc_image_id = fields.Char('Woo Image ID')
    ks_image_name = fields.Char("Images", readonly=True)
    ks_image_id = fields.Many2one('ks.common.product.images', "Odoo Image", ondelete="cascade")
    ks_wc_variant_id = fields.Many2one('ks.woo.product.variant', string='Product template', ondelete='cascade')
    ks_wc_template_id = fields.Many2one('ks.woo.product.template', string='Product variant', ondelete='cascade')
    ks_image = fields.Binary('Image', attachment=False)
    # ks_image_1 = fields.Binary(string='Images', attachment=False)
    ks_url = fields.Char(string="Image URL", help="External URL of image")
    sequence = fields.Integer(help="Sequence of images.", index=True, default=10)

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            record = super(KsWooProductImage, self).create(values)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            rec_id = str(record.id)
            if not record.ks_wc_image_id:
                record.ks_image_name = "{image_name}_{image_id}.png".format(image_name=record.ks_name,
                                                                            image_id=rec_id)
                record.ks_image_name = record.ks_image_name.replace(" ", "_")
                image_url = base_url + '/ks_wc_image/%s/%s/%s/%s' % (
                    self.env.cr.dbname,
                    str(self.env.user.id),
                    rec_id,
                    record.ks_image_name)
                record.write({'ks_url': image_url})

        return record

    def ks_odoo_prepare_image_data(self, image, template_id=False, variant_id=False):
        image_exist = self.search([('ks_image_id', '=', image.id),
                                   ('ks_wc_template_id', '=', template_id),
                                   ('ks_wc_variant_id', '=', variant_id)])
        if image_exist:
            image_exist.write({
                'ks_image': image.ks_image,
                'ks_name': image.ks_name
            })
        else:
            values = {
                "ks_image": image.ks_image,
                'ks_name': image.ks_name,
                'ks_image_id': image.id,
                'ks_wc_template_id': template_id,
                'ks_wc_variant_id': variant_id,
            }
            image_exist = self.create(values)
        return image_exist

    def ks_prepare_variant_images_for_woo(self, layer_product=False):
        values = {}
        values = {
            "src": self.ks_url,
        }
        if self.ks_wc_image_id:
            values.update({
                "id": int(self.ks_wc_image_id)
            })
        return values

    def ks_prepare_images_for_woo(self, layer_product=False):
        if len(self) <= 1:
            values = {}
            values = {
                "src": self.ks_url,
            }
            if self.ks_wc_image_id:
                values.update({
                    "id": int(self.ks_wc_image_id)
                })
            return [values]
        else:
            images = []
            if layer_product:
                if layer_product.profile_image:
                    values = {
                        "src": layer_product.profile_image.ks_url,
                    }
                    if layer_product.profile_image.ks_wc_image_id:
                        values.update({
                            "id": int(layer_product.profile_image.ks_wc_image_id)
                        })
                    images.append(values)
                self = self.filtered(lambda x: x.id != layer_product.profile_image.id)
            for rec in self:
                values = {
                    "src": rec.ks_url,
                }
                if rec.ks_wc_image_id:
                    values.update({
                        "id": int(rec.ks_wc_image_id)
                    })
                images.append(values)
            return images
    def ks_update_images_for_odoo(self, images, product=False, variant=False):
        image_count = 0
        if images:
            for index, image_data in enumerate(images):
                image_src = image_data.get('src')
                image = self.env['ks.common.product.images'].get_image_from_url(image_src)
                product_template = self.env["ks.woo.product.template"].browse(product)

                image_record = self.search([('ks_wc_image_id', '=', image_data.get('id')),
                                                ('ks_wc_template_id', '=', product)])
                if not image_record and product:
                    image_record = self.ks_get_image_record(image_src,product)

                if image_record:
                    image_record.write({
                        "ks_wc_image_id": image_data.get('id'),
                        "ks_image": image,
                        "ks_url": image_data.get('src'),
                        "ks_name": image_data.get('name'),
                        "ks_image_name": image_data.get('name'),
                    })

                else:
                    product_template = self.env["ks.woo.product.template"].browse(product)
                    main_image_exists = self.env['ks.common.product.images'].create({
                        "ks_name": image_data.get('name'),
                        "ks_template_id": product_template.ks_product_template.id,
                        "ks_image": image,
                        "ks_url": image_data.get('src'),
                    })
                    self.create({
                        "ks_wc_image_id": image_data.get('id'),
                        "ks_image": image,
                        "ks_image_id": main_image_exists.id,
                        "ks_url": image_data.get('src'),
                        "ks_wc_variant_id": variant,
                        "ks_wc_template_id": product,
                        "ks_name": image_data.get('name'),
                        "ks_image_name": image_data.get('name'),
                    })
                if product and index == 0:
                    product_template = self.env["ks.woo.product.template"].browse(product)
                    odoo_product = product_template.ks_product_template
                    if image and odoo_product.image_1920 != image:
                        odoo_product.with_context(woo_sync=True).write({'image_1920': image})

    def ks_manage_variant_images_for_odoo(self, variations, instance, product):
        """
        :param variations: list of woocommerce variant ids
        :param product: ks.woo.product.template()
        :return:
        """
        if variations:
            for id in variations:
                product_json_data = self.env['ks.woo.product.template'].ks_woo_get_product(id, instance)
                if product_json_data:
                    images = product_json_data.get("images")
                    variant = product.ks_wc_variant_ids.filtered(
                        lambda x: (x.ks_wc_instance.id == instance.id) and (x.ks_wc_product_tmpl_id.id == product.id)
                                  and (x.ks_woo_variant_id == id))
                    if images:
                        image_data = images[0]
                        image_src = image_data.get('src')
                        image = self.env['ks.common.product.images'].get_image_from_url(image_src)
                        image_record = self.search([('ks_wc_image_id', '=', image_data.get('id')),
                                                        ('ks_wc_template_id', '=', product.id),
                                                        ('ks_wc_variant_id', '=', variant.id)])
                        if not image_record:
                            image_record = self.ks_get_image_record(image_src,product)

                        if image_record:
                            image_record.write({
                                "ks_wc_image_id": image_data.get('id'),
                                "ks_image": image,
                                "ks_url": image_src,
                                "ks_wc_variant_id": variant,
                                "ks_wc_template_id": product,
                                "ks_name": image_data.get('name')
                            })
                        else:
                            # main_image = self.env['ks.common.product.images'].create({
                            #     "ks_name": image_data.get('name'),
                            #     "ks_template_id": product.ks_product_template.id,
                            #     "ks_variant_id": variant.ks_product_variant.id,
                            #     "ks_image": image,
                            #     "ks_url": image_data.get('src'),
                            # })
                            #
                            # self.create({
                            #     "ks_wc_image_id": image_data.get('id'),
                            #     "ks_image": image,
                            #     "ks_image_id": main_image.id,
                            #     "ks_url": image_src,
                            #     "ks_wc_variant_id": variant.id,
                            #     "ks_wc_template_id": product.id,
                            #     "ks_name": image_data.get('name')
                            # })

                            variant.ks_product_variant.with_context(woo_sync=True).write({"image_1920": image})

    def ks_get_image_record(self, image_url, product):
        if image_url:
            image_url_split = image_url.split("/")
            if image_url_split:
                image_name = image_url_split[-1:]
                if image_name:
                    image_name = image_name[0].split('.')
                    image_name = image_name[0].split('-')
                    image_name = image_name[0].split('_')
                    if len(image_name) >= 2:
                        image_id = image_name[-1:]
                        if image_id:
                            try:
                                image_id = int(image_id[0])
                                image_record = self.search([('id', '=', image_id),('ks_wc_template_id','=',product)])
                                return image_record
                            except Exception:
                                return False
        return False
