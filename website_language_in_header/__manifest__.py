# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Website Language In Header",
    'summary': 'Put website language switcher in header',
    'description': """Put website language switcher in header """,
    'category': 'CybEye',
    'version': '1.0',
    'depends': ['website'],
    'installable': True,
    'data': [
        'views/website_template.xml',
    ],
}
