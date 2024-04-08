import base64
import xlsxwriter
from dateutil.relativedelta import relativedelta
from PyPDF2.pdf import BytesIO
from odoo import fields, models, _
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from datetime import datetime


class WizardPrintInvoiceReport(models.TransientModel):
    _name = "wizard.print.invoice.report"

    # date_from = fields.Date(string='Date From', required=True, help="End date",
    #                         default=lambda self: fields.Date.to_string(
    #                             (datetime.now().replace(day=1))))
    # date_to = fields.Date(string='Date To', required=True, help="End date",
    #                     default=lambda self: fields.Date.to_string(
    #                         (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    name = fields.Char(string='File Name', readonly=True)
    data = fields.Binary(string='File', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')

    # def check_date_range(self):
    #     if self.date_to < self.date_from:
    #         raise ValidationError(_('End Date should be greater than Start Date.'))

    def go_back(self):
        self.state = 'choose'
        return {
            'name': 'INVOICE REPORT',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new'
        }
