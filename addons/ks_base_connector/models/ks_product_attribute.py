# -*- coding: utf-8 -*-

from odoo import models
import logging
_logger = logging.getLogger(__name__)


class KsBaseProductAttributeInherit(models.Model):
    _inherit = "product.attribute"

    def ks_manage_attribute_in_odoo(self, attribute_string, attribute_type='radio', create_variant='always',
                                    odoo_attribute= False):
        """
        Gives attribute if found, otherwise creates new one and returns it.
        :param attribute_string: name of attribute
        :param attribute_type: type of attribute
        :param create_variant: when variant create
        :return: attributes
        """
        try:
            attributes = self.search([('name', '=ilike', attribute_string),
                                      ('create_variant', '=', create_variant)])
            values = {'name': attribute_string,
                      'create_variant': create_variant,
                      'display_type': attribute_type}
            if not attributes and not odoo_attribute:
                attributes = self.create(values)
            if odoo_attribute:
                odoo_attribute.write(values)
            else:
                attributes.write(values)
            return attributes
        except Exception as e:
            _logger.info(str(e))

