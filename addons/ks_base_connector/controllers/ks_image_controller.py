# -*- coding: utf-8 -*-

import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class KsImageUrl(http.Controller):
    @http.route('/ks_image/<string:encoded_db>/<string:encoded_uid>/<string:encoded_image_id>', type='http', auth='none',
                csrf=False, website=False, methods=['GET', 'POST'])
    def get_image_from_url(self, encoded_db='', encoded_uid='', encoded_image_id='', **kwargs):
        if encoded_db and encoded_uid and encoded_image_id:
            encoded_db, encoded_uid, encoded_image_id = encoded_db.strip(), encoded_uid.strip(), encoded_image_id.strip()
            decoded_db = base64.urlsafe_b64decode(encoded_db)
            db = str(decoded_db, "utf-8")
            decoded_uid = base64.urlsafe_b64decode(encoded_uid)
            uid = str(decoded_uid, "utf-8")
            request.session.db = db
            request.session.uid = uid
            try:
                decoded_image_data = base64.urlsafe_b64decode(encoded_image_id)
                image_id = str(decoded_image_data, "utf-8")
                status, response_headers, content = request.env['ir.http'].sudo().binary_content(
                    model='ks.common.product.images', id=image_id,
                    field='ks_image')
                image_content_base64 = base64.b64decode(content) if content else ''
                _logger.info("Image found with status %s", str(status))
                response_headers.append(('Content-Length', len(image_content_base64)))
                return request.make_response(image_content_base64, response_headers)
            except Exception:
                return request.not_found()
        return request.not_found()
