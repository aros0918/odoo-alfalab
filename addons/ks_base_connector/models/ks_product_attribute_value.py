# -*- coding: utf-8 -*-

from odoo import models
import logging
_logger = logging.getLogger(__name__)


class KsProductAttributeValueInherit(models.Model):
    _inherit = "product.attribute.value"

    def ks_manage_attribute_value_in_odoo(self, name, attribute_id, odoo_attribute_value=False):
        """
        Gives attribute value if found, otherwise creates new one and returns it.
        :param name: name of attribute value
        :param attribute_id:id of odoo attribute
        :return: attribute values
        """
        try:
            attribute_values = self.search([('name', '=ilike', name), ('attribute_id', '=', attribute_id)])
            value = {'name': name,
                     'attribute_id': attribute_id
                     }
            if not attribute_values and not odoo_attribute_value:
                return self.create(value)
            elif odoo_attribute_value:
                odoo_attribute_value.write(value)
            else:
                attribute_values.write(value)
            return attribute_values
        except Exception as e:
            _logger.info(str(e))


