# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_volume_volume_in_cubic_feet = fields.Selection(selection_add=[('2', 'Cubic Centi Meter')],
                                                           config_parameter='product.volume_in_cubic_feet', default='0')
