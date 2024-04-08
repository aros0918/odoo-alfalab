import logging

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


_logger = logging.getLogger(__name__)


class KsSalesPrintReportWizard(models.TransientModel):
    _name = "ks.sales.print.report.wizard"
    _description = "Sales Print Report"
    _rec_name = 'ks_wc_instance'

    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance id",
                                     domain=[('ks_instance_state', '=', 'active')], required=True)

    def action_sales_report_generate(self):
        return self.env.ref('ks_woocommerce.ks_woocommerce_inst_sales_report_id').report_action(self)

    def get_today_date(self):
        return str(date.today())

    def get_order_count_per_instance(self, instance_id):
        """
        Counts orders
        :param instance_id: woo instance
        :return: counts of orders per instance
        """
        return self.env['sale.order'].search_count([('ks_wc_instance', '=', instance_id), ('state', 'not in', ['cancel', 'draft'])])

    def get_total_orders(self):
        """
        Get total orders for an instance
        :return: count
        """
        count = 0
        for rec in self.ks_wc_instance:
            count += self.env['sale.order'].search_count([('ks_wc_instance', '=', rec.id), ('state', 'not in', ['cancel', 'draft'])])
        return count

    def get_order_lines(self, instance_id):
        """
        fetched order lines
        :param instance_id: woo instance
        :return: order lines
        """
        domain = [('state', 'not in', ['cancel', 'draft']),
                  ('ks_wc_instance', '=', instance_id)]
        return self.env['sale.order'].search(domain)


