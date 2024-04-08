# -*- coding: utf-8 -*-
{
	'name': 'Odoo Base Connector',

	'summary': """
This is a base for all Connector provided
""",

	'description': """
Webhook Connector Apps
            Odoo Webhook Apps
            Best Webhook Connector Apps
            Odoo Woocommerce Connectors
            Woocommerce Connectors
            Woo commerce Connectors
            Woocommerce Apps
            Woo commerce Apps
            Woo-commerce Apps
            Best Woocommerce Apps
            Best Woo commerce Apps
            Real Time Syncing
            Import Export Data Apps
            V16 Woocommerce
            Woocommerce V16
            One Click Data Sync
            Instance Apps
            API sync Apps
            API integration
            Bidirectional Sync
            Bidirectional Apps
            Multiple Woocommerce store
            Multiple Woo store
            Woo Odoo Bridge
            Inventory Management Apps
            Update Stock Apps
            Best Woo Apps
            Best Connector Apps
            Woocommerce Bridge
            Odoo Woocommerce bridge
            Woo commerce bridge
            Auto Task Apps
            Auto Job Apps
            Woocommerce Order Cancellation
            Order Status Apps
            Order Tracking Apps
            Order Workflow Apps
            Woocommerce Order status Apps
            Connector For Woocommerce
""",

    'author': "Ksolves India Ltd.",
    'website': "https://store.ksolves.com/",
    'category': 'Sales',
    'version': '1.0.2',
    'application': True,
    'license': 'OPL-1',
    'currency': 'EUR',
    'price': 26.25,
    'maintainer': 'Ksolves India Ltd.',
    'support': 'sales@ksolves.com',
    'images': ['static/description/ks_base_connector.gif'],
    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'sale_stock', 'stock', 'sale_management'],
    'data': ['security/ir.model.access.csv',
             'views/ks_common_product_images_view.xml',
             'views/ks_product_view.xml',
             'views/ks_product_template_view.xml',
             'views/ks_sale_workflow_conf_view.xml',
             'wizards/ks_message_wizard.xml',
             'views/ks_sale_order_view.xml',
             'data/automatic_workflow_data.xml',
             'data/ir_cron.xml',
             'data/ks_uom_data.xml',
             ],
    # 'post_init_hook': 'post_install_hook',

}
