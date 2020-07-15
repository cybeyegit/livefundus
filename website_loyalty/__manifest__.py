# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

{
    'name': "Loyalty and Rewards Program",
    'summary': """Reward Your Loyal Customers!""",
    'description': """Loyalty & Rewards App For Odoo
Odoo Loyalty Program App
Odoo Loyalty Module
Odoo Website Loyalty Management
Odoo Bonus Program""",
    'author': "AppJetty",
    'license': 'OPL-1',
    'website': "https://www.appjetty.com",
    'category': 'Sales',
    'version': '13.0.1.0.0',
    'depends': ['sale_management', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'views/report_sale_order.xml',
        'views/menu_loyalty.xml',
        'views/loyalty_history_view.xml',
        'views/loyalty_program_view.xml',
        'views/sale_order_view.xml',
        'views/res_users_view.xml',
        'views/res_partner_view.xml',
        'views/templates.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
    ],
    'images': ['static/description/splash-screen.png'],
    'price': 49.00,
    'currency': 'EUR',
    'support': 'support@appjetty.com',
}
