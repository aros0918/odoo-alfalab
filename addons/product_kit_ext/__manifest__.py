# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Product Kit',
    'version': '1.0',
    'summary': 'Provide features of Combo(Kit) Product.',
    'description': """
    Combo Product.
    Kit product
    product
    stock
    inventory
    """,
    'category': 'Sales',
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'www.synconics.com',
    'depends': ['sale_management', 'sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_view.xml',
        'views/sale_view.xml',
        'report/sale_portal_templates.xml',
        'report/sale_report_templates.xml',
        'report/report_invoice.xml',
    ],
    'demo': [],
    'images': [
        'static/description/main_screen.png'
    ],
    'price': 49.0,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}
