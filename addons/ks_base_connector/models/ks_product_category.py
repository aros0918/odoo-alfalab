from odoo import models, fields
import logging
_logger = logging.getLogger(__name__)


class KsProductCategoryInherit(models.Model):
    _inherit = 'product.category'

    def ks_create_data_in_odoo(self, category_data):
        if category_data:
            try:
                odoo_category = self.create(category_data)
                return odoo_category
            except Exception as e:
                _logger.info(str(e))

    def ks_update_data_in_odoo(self, odoo_category, category_data):
        if category_data and odoo_category:
            try:
                odoo_category.write(category_data)
            except Exception as e:
                _logger.info(str(e))


