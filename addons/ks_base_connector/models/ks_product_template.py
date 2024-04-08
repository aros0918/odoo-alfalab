from odoo import models, fields, api


class KsProductTemplateExtended(models.Model):
    _inherit = "product.template"

    ks_length = fields.Float()
    ks_width = fields.Float()
    ks_height = fields.Float()
    ks_image_ids = fields.One2many('ks.common.product.images', 'ks_template_id', string='Images')
    profile_image_id = fields.Many2one("ks.common.product.images", string = "Profile Image", readonly = True)

    @api.onchange('ks_length', 'ks_width', 'ks_height')
    def onchange_l_b_h(self):
        """
        This will calculate the value for Volume with respective of ks_length, ks_width and ks_height

        :return: None
        """
        self.volume = float(self.ks_length if self.ks_length else 0) * float(
            self.ks_width if self.ks_width else 0) * float(
            self.ks_height if self.ks_height else 0)

    def ks_prepare_common_image_values(self, values):
        """
        This will prepare image dictionary data
        :param values: dictionary of values
        :return: the image dictionary.
        """
        image_values = {"sequence": 0,
                        "ks_image": values.get("image_1920", False),
                        "ks_name": self.name,
                        "ks_template_id": self.id}
        return image_values

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            res = super(KsProductTemplateExtended, self).create(values)
            if values.get("image_1920", False) and res and not self.env.context.get("woo_sync"):
                # If product display image gets updated then it will directly add into the ks_image_ids
                image_values = res.ks_prepare_common_image_values(values)
                image_id = self.env["ks.common.product.images"].with_context(main_image=True).create(image_values)
                res.profile_image_id = image_id.id
        return res

    def write(self, values):
        res = super(KsProductTemplateExtended, self).write(values)
        if values.get("image_1920", False) and self:
            for record in self:
                if values.get("image_1920") and not record.env.context.get("woo_sync"):
                    # If product display image gets updated then it will directly add into the ks_image_ids
                    image_values = record.ks_prepare_common_image_values(values)
                    image_id = self.env["ks.common.product.images"].with_context(main_image=True).create(image_values)
                    record.profile_image_id = image_id.id
        return res

    # def ks_manage_template_images(self, woo_product, template):
    #     if template.ks_image_ids:
    #         for image in template.ks_image_ids:
    #             self.env['ks.woo.product.images'].ks_odoo_prepare_image_data(image, template_id=woo_product.id,
    #                                                                          variant_id=False)

    # def ks_manage_product_category(self, woo_product, template):
    #     if template.categ_id:
    #         woo_category = self.env['ks.woo.product.category'].check_if_already_prepared(woo_product.ks_wc_instance,
    #                                                                                      template.categ_id)
    #         if not woo_category:
    #             woo_category = self.env['ks.woo.product.category'].create_woo_record(woo_product.ks_wc_instance,
    #                                                                                  template.categ_id,
    #                                                                                  export_to_woo=False)
    #         woo_product.ks_wc_category_ids = [(4, woo_category.id)]
    #
    # def ks_manage_product_variant(self, woo_product, product_template):
    #     for variant in product_template.product_variant_ids:
    #         product_attr_value_exist = self.env['ks.woo.product.variant'].check_if_already_prepared(
    #             woo_product.ks_wc_instance,
    #             variant)
    #         if product_attr_value_exist:
    #             self.env['ks.woo.product.variant'].update_woo_record(woo_product.ks_wc_instance, variant, woo_product)
    #         else:
    #             self.env['ks.woo.product.variant'].create_woo_record(woo_product.ks_wc_instance, variant, woo_product)

    def ks_create_product_template(self, product_json_data):
        if product_json_data:
            odoo_simple_product = self.create(product_json_data)

        ##Add varibale product condition here only
        return odoo_simple_product

    def ks_update_product_template(self, product_exist, product_json_data):
        if product_exist.ks_product_template and product_json_data:
            product_exist.ks_product_template.write(product_json_data)
            ##Add variable condition here only

    @api.model
    def _get_volume_uom_id_from_ir_config_parameter(self):
        """ Get the unit of measure to interpret the `volume` field. By default, we consider
        that volumes are expressed in cubic meters. Users can configure to express them in cubic feet
        by adding an ir.config_parameter record with "product.volume_in_cubic_feet" as key
        and "1" as value.
        """
        product_length_in_feet_param = self.env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet')
        if product_length_in_feet_param == '2':
            return self.env.ref('ks_base_connector.product_uom_cubic_cm')
        else:
            return super(KsProductTemplateExtended, self)._get_volume_uom_id_from_ir_config_parameter()

