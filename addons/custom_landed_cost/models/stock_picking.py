# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    #inherited the search method and pass order by to see latest id first
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        args = args.copy()
        if self._context.get('display') == 'yes':
            domain = [('id','!=',0)] 	
            order = 'id desc'
        else:
            domain=args
            order = None
        return super(StockPicking, self)._search(domain, offset, limit, order=order, count=count, access_rights_uid=access_rights_uid)
