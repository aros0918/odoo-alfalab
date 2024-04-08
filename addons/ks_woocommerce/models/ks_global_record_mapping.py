# -*- coding: utf-8 -*-

from odoo import models


class KsMapRecordWizard(models.Model):
    _name = "ks.global.record.mapping"
    _description = "Record Mapper"

    def prepare_lines_customer(self, record_ids, model_name):
        """
        Prepared wizard record lines for customer
        :param record_ids: active ids selected
        :param model_name: name of model
        :return: lines
        """
        lines = []
        for line in record_ids:
            vals = {
                'ks_id': line.id,
                'name': line.display_name,
                'ks_base_model_customer':line.id
            }
            lines.append(vals)
        return lines

    def prepare_lines_category(self, record_ids, model_name):
        """
        Prepared wizard record lines for category
        :param record_ids: active ids selected
        :param model_name: name of model
        :return: lines
        """
        lines = []
        inputs = []
        for line in record_ids:
            odoo_category = line
            parent_path = odoo_category.parent_path
            all_ids = list(map(int, parent_path.split("/")[:-1]))
            all_ids.reverse()
            all_odoo_records = line.browse(all_ids)
            if all_odoo_records:
                for line in all_odoo_records:
                    if line.id not in inputs:
                        vals = {
                            'ks_id': line.id,
                            'name': line.display_name,
                            'ks_base_model_category': line.id,
                        }
                        lines.append(vals)
                        inputs.append(line.id)
        return lines

    def action_open_mapping_wizard(self, curr_model, active_record, mapping_name=False):
        """
        opens mapping wizard for customer models
        :param curr_model: current model active
        :param active_record: selected record
        :param mapping_name: boolean, mapping title
        :return:
        """
        model_name = curr_model.model
        record_ids = self.env[model_name].browse(active_record)
        lines = self.prepare_lines_customer(record_ids, curr_model)
        self.env['map.wizard.line'].create(lines)
        return {
            'type': 'ir.actions.act_window',
            'name': model_name if not mapping_name else mapping_name,
            'res_model': 'map.res.partner.wizard',
            'target': 'new',
            'view_id': self.env.ref('ks_woocommerce.ks_partner_wizard_form_view').id,
            'view_mode': 'form',
            'context': {'default_res_partner_line_ids': lines}
        }

    def prepare_lines_attribute(self, record_ids, curr_model):
        """
                Prepared wizard record lines for attributes
                :param record_ids: active ids selected
                :param curr_model: name of model
                :return: lines
                """
        lines = []
        for line in record_ids:
            vals = {
                'ks_id': line.id,
                'name': line.display_name,
                'ks_base_model_attribute': line.id,
            }
            lines.append(vals)
            for value in line.value_ids:
                vals = {
                    'ks_id': value.id,
                    'name': value.display_name,
                    'ks_base_model_attribute_value': value.id,
                }
                lines.append(vals)
        return lines

    def prepare_lines_product(self, record_ids, curr_model):
        """
        Prepared wizard record lines for product
        :param record_ids: active ids selected
        :param curr_model: name of model
        :return: lines
        """
        lines = []
        for line in record_ids:
            vals = {
                'ks_id': line.id,
                'name': line.display_name,
                'ks_base_model_product': line.id,
            }
            lines.append(vals)
            if line.product_variant_count > 1:
                for value in line.product_variant_ids:
                    if value:
                        vals = {
                            'ks_id': value.id,
                            'name': value.display_name,
                            'ks_base_model_product_variant': value.id,
                        }
                        lines.append(vals)
        return lines

    def action_open_category_mapping_wizard(self, curr_model, active_record, mapping_name=False):
        """
        opens category mapping wizard
        :param curr_model: current model
        :param active_record: selected record
        :param mapping_name: name of mapping wizard
        :return:
        """
        model_name = curr_model.model
        record_ids = self.env[model_name].browse(active_record)
        lines = self.prepare_lines_category(record_ids, curr_model)
        self.env['map.wizard.line'].create(lines)
        return {
            'type': 'ir.actions.act_window',
            'name': model_name if not mapping_name else mapping_name,
            'res_model': 'map.product.category.wizard',
            'target': 'new',
            'view_id': self.env.ref('ks_woocommerce.ks_category_wizard_form_view').id,
            'view_mode': 'form',
            'context': {'default_category_line_ids': lines}
        }

    def action_open_attribute_mapping_wizard(self, curr_model, active_record, mapping_name=False):
        """
                opens attribute mapping wizard
                :param curr_model: current model
                :param active_record: selected record
                :param mapping_name: name of mapping wizard
                :return:
                """
        model_name = curr_model.model
        record_ids = self.env[model_name].browse(active_record)
        lines = self.prepare_lines_attribute(record_ids, curr_model)
        self.env['map.wizard.line'].create(lines)
        return {
            'type': 'ir.actions.act_window',
            'name': model_name if not mapping_name else mapping_name,
            'res_model': 'map.product.attribute.wizard',
            'target': 'new',
            'view_id': self.env.ref('ks_woocommerce.ks_attribute_wizard_form_view').id,
            'view_mode': 'form',
            'context': {'default_attribute_line_ids': lines}
        }

    def action_open_product_mapping_wizard(self, curr_model, active_record, mapping_name=False):
        """
                opens product mapping wizard
                :param curr_model: current model
                :param active_record: selected record
                :param mapping_name: name of mapping wizard
                :return:
                """
        model_name = curr_model.model
        record_ids = self.env[model_name].browse(active_record)
        lines = self.prepare_lines_product(record_ids, curr_model)
        self.env['map.wizard.line'].create(lines)
        return {
            'type': 'ir.actions.act_window',
            'name': model_name if not mapping_name else mapping_name,
            'res_model': 'map.product.wizard',
            'target': 'new',
            'view_id': self.env.ref('ks_woocommerce.ks_product_wizard_form_view').id,
            'view_mode': 'form',
            'context': {'default_product_line_ids': lines}
        }
