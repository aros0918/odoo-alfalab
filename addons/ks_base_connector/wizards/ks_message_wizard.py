# -*- coding: utf-8 -*-

from odoo import fields, models


class KsMessageWizard(models.TransientModel):
    _name = "ks.message.wizard"
    _description = "Message wizard to display warnings, alert ,success messages"

    name = fields.Text(string="Message", readonly=True, default=lambda self: self.env.context.get("message", False))

    def ks_pop_up_message(self, names, message):
        """

        :param names: The title of wizard
        :param message: The content to be shown
        :return: open a wizard
        """
        view = self.env.ref('ks_base_connector.ks_message_wizard')
        context = dict(self._context or {})
        context['message'] = message
        return {
            'name': names,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ks.message.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
        }
