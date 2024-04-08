# -*- coding: utf-8 -*-

from odoo import models


class KsBaseAccountMove(models.Model):
    _inherit = 'account.move'

    def ks_prepare_payment_values(self, work_flow_process_record):
        """
        This method prepare payment json data
        :param work_flow_process_record: ks.sale.workflow.configuration() object
        :return: Dict
        """
        return {
            'journal_id': work_flow_process_record.ks_journal_id.id,
            'ref': self.payment_reference,
            'currency_id': self.currency_id.id,
            'payment_type': 'inbound',
            'date': self.date,
            'partner_id': self.commercial_partner_id.id,
            'amount': self.amount_residual,
            'payment_method_id': work_flow_process_record.ks_inbound_payment_method_id.id,
            'partner_type': 'customer'
        }
