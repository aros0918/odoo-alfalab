{
    'name': "Export Selected Invoice Xlsx",
    'category': 'account',
    'depends': ['account'],
    'data': [
        "views/invoice_view.xml",
    ],
    'assets': {
       'web.assets_backend': [
            'export_selected_invoice_xlsx/static/src/xml/exp_tree_button.xml',
            'export_selected_invoice_xlsx/static/src/js/exp_tree_button.js',

       ],
    },
    'author': 'Odoo',
    'version': '16.0.0.0.0',
    'license': 'AGPL-3',
    'sequence': 1,
    'installable': True,
    'application': True,
    'auto_install': False,
}

