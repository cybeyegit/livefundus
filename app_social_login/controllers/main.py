# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import math

import babel.dates
from odoo import http, fields
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.http import request
from odoo.osv import expression
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)


class WebsiteContact(WebsiteProfile):

    def _check_user_profile_access(self, user_id):
        user_sudo = request.env['res.users'].sudo().browse(user_id)
        # User can access - no matter what - his own profile
        if user_sudo.id == request.env.user.id:
            return user_sudo
        if user_sudo.karma == 0 or not user_sudo.website_published or \
                (user_sudo.id != request.session.uid and request.env.user.karma < request.website.karma_profile_min):
            return user_sudo
        return user_sudo

    def get_formated_date(self, event):
        start_date = fields.Datetime.from_string(event.date_begin).date()
        end_date = fields.Datetime.from_string(event.date_end).date()
        month = babel.dates.get_month_names('abbreviated', locale=get_lang(event.env).code)[start_date.month]
        return ('%s %s%s') % (
            month, start_date.strftime("%e"), (end_date != start_date and ("-" + end_date.strftime("%e")) or ""))

    def get_formated_blog_date(self, blog):
        post_date = fields.Datetime.from_string(blog.post_date).date()

        month = babel.dates.get_month_names('abbreviated', locale=get_lang(blog.env).code)[post_date.month]
        return ('%s %s') % (month, post_date.strftime("%e"))

    def get_formated_product_date(self, product):
        create_date = fields.Datetime.from_string(product.create_date).date()

        month = babel.dates.get_month_names('abbreviated', locale=get_lang(product.env).code)[create_date.month]
        return ('%s %s') % (month, create_date.strftime("%e"))

    def _add_user_events(self, user, values):
        events = request.env['event.event'].search([
            ('create_uid', '=', user.id),
            '|',
            ('website_id', '=', request.env['website'].get_current_website().id),
            ('website_id', '=', False)
        ])

        values['user_events'] = []

        for event in events:
            values['user_events'].append({
                "date": self.get_formated_date(event),
                "event": event,
                "url": event.website_url})

    def _add_user_blogs(self, user, values):
        blogs = request.env['blog.post'].search([
            ('create_uid', '=', user.id),
            '|',
            ('website_id', '=', request.env['website'].get_current_website().id),
            ('website_id', '=', False)
        ])

        values['user_blogs'] = []

        for blog in blogs:
            values['user_blogs'].append({
                "date": self.get_formated_blog_date(blog),
                "blog": blog,
                "url": blog.website_url})

    def _add_user_products(self, user, values):
        products = request.env['product.template'].search([
            ('create_uid', '=', user.id),
            '|',
            ('website_id', '=', request.env['website'].get_current_website().id),
            ('website_id', '=', False)
        ])

        values['user_products'] = []

        for product in products:
            values['user_products'].append({
                "date": self.get_formated_product_date(product),
                "product": product,
                "url": product.website_url})

    def _prepare_user_profile_values(self, user, **post):
        values = super(WebsiteContact, self)._prepare_user_profile_values(user, **post)

        self._add_user_events(user, values)
        self._add_user_blogs(user, values)
        self._add_user_products(user, values)

        return values

    @http.route(['/profile/users',
                 '/profile/users/page/<int:page>'], type='http', auth="public", website=True)
    def view_all_users_page(self, page=1, **searches):
        User = request.env['res.users']
        dom = [('website_published', '=', True)]

        # Searches
        search_term = searches.get('search')
        if search_term:
            dom = expression.AND(
                [['|', ('name', 'ilike', search_term), ('company_id.name', 'ilike', search_term)], dom])

        user_count = User.sudo().search_count(dom)

        if user_count:
            page_count = math.ceil(user_count / self._users_per_page)
            pager = request.website.pager(url="/profile/users", total=user_count, page=page, step=self._users_per_page,
                                          scope=page_count if page_count < self._pager_max_pages else self._pager_max_pages)

            users = User.sudo().search(dom, limit=self._users_per_page, offset=pager['offset'], order='karma DESC')
            user_values = self._prepare_all_users_values(users)

            # Get karma position for users (only website_published)
            position_domain = [('website_published', '=', True)]
            position_map = self._get_users_karma_position(position_domain, users.ids)
            for user in user_values:
                user['position'] = position_map.get(user['id'], 0)

            values = {
                'top3_users': user_values[:3] if not search_term and page == 1 else None,
                'users': user_values[3:] if not search_term and page == 1 else user_values,
                'pager': pager
            }
        else:
            values = {'top3_users': [], 'users': [], 'search': search_term, 'pager': dict(page_count=0)}

        return request.render("website_profile.users_page_main", values)
