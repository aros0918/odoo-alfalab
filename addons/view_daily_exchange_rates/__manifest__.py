# -*- coding: utf-8 -*-
# TODO : Update to use/create a "Letter" paper format instead of A4.
{
    'name': 'Daily Exchnage Rate On Sale Order, Invoices ',
    'summary': 'This module used to check currency exchange rates from sale orders and invoices',
    'description': 'This module used to check currency exchange rates from sale orders and invoices',
    'author': 'MP Technolabs',
    'website': 'https://www.mptechnolabs.com/',
    'category': 'Accounting/Accounting',
    'version': '16.0.0.1',
    'depends': ['account','sale_management'],
    'data':[
            'views/sale_order.xml',
            'views/account_move.xml',
            'views/res_currency_rate.xml',
    	   ],
    'application': True,
    'license': 'LGPL-3',

}
