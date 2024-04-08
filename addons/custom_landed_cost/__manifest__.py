# -*- coding: utf-8 -*-
# TODO : Update to use/create a "Letter" paper format instead of A4.
{
    'name': 'Custom Landed Cost',
    'summary': 'This module used for customization in landed cost module for reverse and delete',
    'description': 'Module used to customize the landed cost method ',
    'author': 'Stepan',
    'website': '',
    'category': 'Operations/Inventory',
    'version': '16.0.0.1',
    'depends': ['stock','stock_landed_costs','purchase'],
    'data':[
    	     'views/landed_cost.xml',
    	   ],
    'application': True,
    'license': 'LGPL-3',

}
