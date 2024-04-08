from odoo import fields, models, api
from odoo.exceptions import ValidationError


class KsWooMetaMapping(models.Model):
    _name = "ks.woo.meta.mapping"
    _description = "Woo Meta Mapping"
    _rec_name = "ks_key"

    ks_model_id = fields.Many2one("ir.model", string="Woo Model", help="Displays odoo default models")
    ks_key = fields.Char(string="Woo Meta Key", required=True, help="Displays the Woo ID")
    ks_fields = fields.Many2one("ir.model.fields", string = "Meta Mapping Field",
                                domain="[('model_id', '=', ks_model_id)]", help="Displays fields of the particular selected model")
    ks_active = fields.Boolean(string="Active", help="Enables/Disables state")
    ks_wc_instance = fields.Many2one("ks.woo.connector.instance", string="Instance Id")

    @api.constrains("ks_model_id", "ks_fields")
    def _check_null_values(self):
        if not self.ks_fields or not self.ks_model_id:
            raise ValidationError("Either of Model or Fields is Empty")

