odoo.define('export_selected_invoice_xlsx.tree_button', function (require) {
"use strict";
var ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');
var DataExport = require('web.DataExport');

var TreeButton = ListController.extend({
   buttons_template: 'export_selected_invoice_xlsx.buttons',
   events: _.extend({}, ListController.prototype.events, {
       'click .export_invoice_action': '_ExportInvoice',
   }),

   _getCustomExportDialogWidget() {
        let state = this.model.get(this.handle);
        // let defaultExportFields = this.renderer.columns.filter(field => field.tag === 'field' && state.fields[field.attrs.name].exportable !== false).map(field => field.attrs.name);
        // console.log("-----------------apple----------------");
        // console.log(defaultExportFields);
        let desiredFields = ['invoice_date', 'name', 'ref', 'invoice_date_due', 'amount_total_in_currency_signed']; // Add your desired field names here
        // Filter out the desired fields from the available columns
        let defaultExportFields = desiredFields.filter(fieldName => state.fields[fieldName] && state.fields[fieldName].exportable !== false);

        let groupedBy = this.renderer.state.groupedBy;
        const domain = [["id", "in", this.getSelectedIds()]];
        return new DataExport(this, state, defaultExportFields, groupedBy,
            domain, this.getSelectedIds());
    },

   _ExportInvoice: function () {
       return this._rpc({
            model: 'ir.exports',
            method: 'search_read',
            domain: [["id", "in", this.getSelectedIds()]],
        }).then(() => this._getCustomExportDialogWidget().export())

   }
});
var InvoiceListView = ListView.extend({
   config: _.extend({}, ListView.prototype.config, {
       Controller: TreeButton,
   }),
});
viewRegistry.add('button_in_tree', InvoiceListView);
});