# -*- coding: utf-8 -*-
{
    'name': 'Odoo WooCommerce Connector',
    'summary': """
           Woocommerce Odoo Connector integrates Odoo with Woocommerce. 
           Manage your Woocommerce store in Odoo. woocommerce,
           woo commerce,wocommerce,odoo woocommerce connector,
           odoo woocommerce integration,odoo for woocommerce,
           woocommerce odoo connector,woocommerce odoo integration,
           odoo woocommerce,odoo wordpress woocommerce connector,
           odoo and woocommerce,connect odoo to woocommerce,
           woocommerce connector odoo,odoo connector woocommerce,integrate odoo with woocommerce,
           ksolves odoo connector,ksolves woocommerce connector,
           ksolves odoo woocommerce connector,odoo connector,woocommerce connector,
           odoo woocommerce connector install,odoo multichannel woocommerce connector,odoo app connector,
           odoo connector tutorial,odoo ecommerce connector,odoo module connector ecommerce,
           odoo wordpress connector,wordpress odoo connector,bi-directional connector,bi-directional,
           bi-directional data exchange,odoo,WooCommerce odoo bridge,Handle Woocommerce orders in Odoo,
           Ecommerce Connector multi channel ,multi-channel woocommerce, multichannel woocommerce bridge, 
           odoo woocommerce extensions for multichannel""",

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
            V13 Woocommerce
            Woocommerce V13
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
    'version': '1.0.5',
    'application': True,
    'license': 'OPL-1',
    'currency': 'EUR',
    'price': 221.704,
    'maintainer': 'Ksolves India Ltd.',
    'support': 'sales@ksolves.com',
    'images': ['static/description/Spring sale horizontal Odoo Video.gif'],
    # any module necessary for this one to work correctly
    'live_test_url': 'http://woocommerce15.kappso.in/web/demo_login',

    'depends': ['base', 'mail', 'sale_management', 'stock', 'ks_base_connector', 'delivery'],
    'data': [
        'security/ks_security.xml',
        'security/ir.model.access.csv',
        'security/ks_woo_commerce_model_security.xml',
        # 'views/ks_assets.xml',
        'wizards/ks_woo_operations_views.xml',
        'wizards/ks_queue_job_views.xml',
        'wizards/ks_product_config_view.xml',
        'wizards/ks_woo_update_product_configuration_view.xml',
        # 'views/ks_account_tax.xml',
        'views/ks_woo_connector_instance_views.xml',
        'views/ks_woo_auto_product_sync.xml',
        'views/ks_woo_customer_sync_view.xml',
        'views/ks_product_attribute_view.xml',
        'views/ks_woo_product_attribute_view.xml',
        'views/ks_woo_product_attr_value.xml',
        'views/ks_woo_product_template_view.xml',
        'views/ks_product_template_view.xml',
        'views/ks_woo_product_variant_view.xml',
        'views/ks_woo_partner_view.xml',
        'views/ks_res_partner_view.xml',
        'views/ks_woo_coupons_view.xml',
        'views/ks_sale_order_view.xml',
        'views/ks_woo_auto_sale_workflow.xml',
        'views/ks_woo_email_report.xml',
        'views/ks_reverse_workflow.xml',
        'views/ks_account_move_view.xml',
        'views/ks_woo_sales_reporting.xml',
        'views/ks_woo_product_tag_view.xml',
        'views/ks_woo_meta_mapping_view.xml',
        'views/ks_woo_product_category_view.xml',
        'views/ks_product_category_view.xml',
        'views/ks_woo_payment_gateway_view.xml',
        'views/ks_woo_delivery_details.xml',
        'views/ks_product_pricelist_item_views.xml',
        'views/ks_woo_webhook_logs.xml',
        'wizards/ks_prepare_to_export_views.xml',
        'wizards/ks_mapping_product_attribute_views.xml',
        'wizards/ks_mapping_product_category_views.xml',
        'wizards/ks_mapping_product_views.xml',
        'wizards/ks_mapping_res_partner_views.xml',
        'wizards/ks_base_instance_selection_views.xml',
        'wizards/ks_print_sales_report.xml',
        'wizards/ks_reset_credentials_view.xml',
        'views/ks_woo_product_images_view.xml',
        'views/ks_woo_logs_views.xml',
        'views/ks_woo_shipping_methods_view.xml',
        'reports/generate_report.xml',
        'reports/ks_inst_sales_report.xml',
        'reports/report.xml',
        'data/ks_email_template.xml',
        'data/ks_woo_partner_data.xml',
        'data/ks_product_product_data.xml',
        'data/ks_dashboard_data.xml',
        'data/ks_order_status_data.xml',
        'data/ks_automation.xml',
        'models/dashboard/ks_woodashboard_view.xml',
        'views/ks_woo_menus.xml'
    ],
    'post_init_hook': 'post_install_hook',

    'external_dependencies': {
        'python': ['woocommerce'],
    },
    'assets': {
        'web.assets_backend': [
            'ks_woocommerce/static/src/css/dashboard.css',
            'ks_woocommerce/static/lib/js/Chart.bundle.min.js',
            'ks_woocommerce/static/lib/js/Chart.js',
            'ks_woocommerce/static/lib/js/Chart.js',
            'ks_woocommerce/static/lib/js/chartjs-plugin-datalabels.js',
            'ks_woocommerce/static/src/css/ks_graph_view.css',
            'ks_woocommerce/static/src/js/ks_graph_owl_widget.js',
            'ks_woocommerce/static/src/css/style.css',
            'ks_woocommerce/static/src/xml/**/*',
        ],
    }
}
