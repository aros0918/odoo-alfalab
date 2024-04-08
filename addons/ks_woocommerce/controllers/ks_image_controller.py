# -*- coding: utf-8 -*-

import base64
import logging

import requests
from odoo import http
from odoo.http import request
# from odoo.addons.web.controllers.main import ensure_db
from odoo.addons.web.controllers.home import Home, ensure_db
from odoo.addons.web.controllers.binary import Binary
_logger = logging.getLogger(__name__)


class KsWooCommerceImageUrl(Home):
    @http.route('/ks_wc_image/<string:db_name>/<string:uid>/<string:image_id>/<string:image_name>',
                type='http', auth='none', csrf=False, methods=['GET', 'POST'])
    def get_image_from_url(self,  db_name='', uid='', image_id='', **kwargs):
        if db_name and uid and image_id:
            db_name, uid, image_id = db_name.strip(), uid.strip(), image_id.strip()
            request.session.db = db_name
            request.session.uid = int(uid)
            try:
                status =  request.env['ir.binary']._get_image_stream_from(
                request.env['ks.woo.product.images'].search([('id','=',int(image_id))]),
                    'ks_image',
                )
                image_content_base64 = status.data
                # _logger.info("Image found with status %s", str(status))
                # headers.append(('Content-Length', len(image_content_base64)))
                return request.make_response(image_content_base64, headers=[('Content-Type', 'image/png')])
            except Exception as e:
                return request.not_found()
        return request.not_found()