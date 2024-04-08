
from odoo import api, fields, models, _
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import xlsxwriter
import base64
import calendar
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def get_invoice_list(self):
        invoice_list = []
        for inv in self:

            date = inv.invoice_date
            name = inv.name
            ref = inv.ref
            due_date = inv.invoice_date_due
            tax_totals = inv.tax_totals
            subtotals = inv.amount_untaxed
            total = inv.amount_total
            taxfive = 0.0
            taxten = 0.0
            taxoneeight = 0.0
            taxfivebase = 0.0
            taxtenbase = 0.0
            taxoneeightbase = 0.0
            subtotal_to_show = ''
            print("======tax_totals=====", inv.tax_totals)
            for subtotal in inv.tax_totals['subtotals']:
                subtotal_to_show = subtotal['name']
            for tax in inv.tax_totals['groups_by_subtotal'][subtotal_to_show]:
                print("======tax=====", tax)
                if tax['tax_group_name'] == 'VAT amount 5%':
                    taxfive = taxfive + tax['tax_group_amount']
                    taxfivebase = taxfivebase + tax['tax_group_base_amount']
                if tax['tax_group_name'] == 'VAT amount 10%':
                    taxten = taxfive + tax['tax_group_amount']
                    taxtenbase = taxtenbase + tax['tax_group_base_amount']
                if tax['tax_group_name'] == 'VAT amount 18%':
                    taxoneeight = taxfive + tax['tax_group_amount']
                    taxoneeightbase = taxoneeightbase + tax['tax_group_base_amount']

            data = {
                'date': date,
                'name': name,
                'ref': ref,
                'subtotals': subtotals,
                'taxfivebase': taxfivebase,
                'taxtenbase': taxtenbase,
                'taxoneeightbase': taxoneeightbase,
                'due_date': due_date,
                'taxfive': taxfive,
                'taxten': taxten,
                'taxoneeight': taxoneeight,
                'total': total,
            }
            _logger.debug('=============== %s', self._name, tax_totals)

            invoice_list.append(data)
        return invoice_list

    def print_invoice_excel_report(self):
        # self.check_date_range()
        xls_filename = 'invoice_report.xlsx'
        workbook = xlsxwriter.Workbook('/tmp/' + xls_filename)
        worksheet = workbook.add_worksheet("invoices")
        invoice_list = self.get_invoice_list()

        # Format
        header_merge_format = workbook.add_format(
            {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 10,
             'bg_color': '#D3D3D3', 'border': 1})
        header_data_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 10,
                                                  'border': 1})
        header_data_format_date = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 10,
                                                       'border': 1, 'num_format': 'dd/mm/yyyy'})
        product_header_format = workbook.add_format({'valign': 'vcenter', 'font_size': 10, 'border': 1})

        # Initial value
        rows = 2
        no = 0
        for inv in invoice_list:
            no = no + 1
            # ------------------------------ Main Table Header --------------------------------
            worksheet.write(1, 0, "No", header_merge_format)
            worksheet.write(1, 1, "Invoice date", header_merge_format)
            worksheet.write(1, 2, "Document number", header_merge_format)
            worksheet.write(1, 3, "Reference number ", header_merge_format)
            worksheet.write(1, 4, "Value for VAT 5%", header_merge_format)
            worksheet.write(1, 5, "Value for VAT 10%", header_merge_format)
            worksheet.write(1, 6, "Value for VAT 18%", header_merge_format)
            worksheet.write(1, 7, "Due date", header_merge_format)
            worksheet.write(1, 8, "VAT amount 5%", header_merge_format)
            worksheet.write(1, 9, "VAT amount 10%", header_merge_format)
            worksheet.write(1, 10, "VAT amount 18%", header_merge_format)
            worksheet.write(1, 11, "Total of the invoice", header_merge_format)


            # --------------------------------- Display Total --------------------------------
            worksheet.write(rows, 0, no, header_data_format)
            worksheet.write(rows, 1, inv['date'], header_data_format_date)
            worksheet.write(rows, 2, inv['name'], header_data_format)
            worksheet.write(rows, 3, inv['ref'], header_data_format)
            worksheet.write(rows, 4, inv['taxfivebase'], header_data_format)
            worksheet.write(rows, 5, inv['taxtenbase'], header_data_format)
            worksheet.write(rows, 6, inv['taxoneeightbase'], header_data_format)
            worksheet.write(rows, 7, inv['due_date'], header_data_format_date)
            worksheet.write(rows, 8, inv['taxfive'], header_data_format)
            worksheet.write(rows, 9, inv['taxten'], header_data_format)
            worksheet.write(rows, 10, inv['taxoneeight'], header_data_format)
            worksheet.write(rows, 11, inv['total'], header_data_format)


            # worksheet.write(rows, 6, inv['narrative'], header_data_format)
            # --------------------------------------------------------------------------------
            rows += 1

        workbook.close()
        erp_wizard_obj = self.env['wizard.print.invoice.report']
        erp_wizard_id = erp_wizard_obj.create({
            # 'state': 'get',
            'data': base64.b64encode(open('/tmp/' + xls_filename, 'rb').read()),
            'name': xls_filename
        })
        return {
            'name': 'Invoice Report',
            'type': 'ir.actions.act_window',
            'res_model': erp_wizard_id._name,
            'view_mode': 'form',
            'res_id': erp_wizard_id.id,
            'target': 'new'
        }