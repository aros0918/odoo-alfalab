# -*- coding: utf-8 -*-
{
    'name': "ERP INVOICE EXCEL REPORT",

    'summary': """
    
        Developed to download invoices based on select lines
        
        """,

    'description': """
        Developed to download invoices based on select lines
    """,

    # Author
    'author': 'ERP CAMBODIA',
    'website': 'https://www.erpcambodia.biz/',
    'maintainer': 'ERP CAMBODIA',


    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'ERP CUSTOM',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'wizards/views.xml',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'license': 'LGPL-3',
    'installable': True,
}