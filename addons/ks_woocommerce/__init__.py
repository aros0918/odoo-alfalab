# -*- coding: utf-8 -*-

from . import wizards
from . import models
from . import controllers
from . import security

from odoo.api import Environment, SUPERUSER_ID


def post_install_hook(cr, registry):
    """
    This will provide access of the module to the existing users at the time of installation.
    """

    env = Environment(cr, SUPERUSER_ID, {})
    ks_user_data = {"users": [(4, user_id.id) for user_id in (env['res.users'].search([]))]}
    ks_woo_access = env.ref('ks_woocommerce.ks_woocommerce_group')
    ks_woo_access.write(ks_user_data)
