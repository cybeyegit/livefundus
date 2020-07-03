# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.addons.website_profile.controllers.main import WebsiteProfile
import math

from odoo import http, modules, tools
from odoo.http import request
from odoo.osv import expression

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

    @http.route(['/profile/users',
                 '/profile/users/page/<int:page>'], type='http', auth="public", website=True)
    def view_all_users_page(self, page=1, **searches):
        User = request.env['res.users']
        dom = []

        # Searches
        search_term = searches.get('search')
        if search_term:
            dom = expression.AND(
                [['|', ('name', 'ilike', search_term), ('company_id.name', 'ilike', search_term)], dom])

        if not search_term:
            dom.append(('is_published', '=', True))

        user_count = User.sudo().search_count(dom)

        if user_count:
            page_count = math.ceil(user_count / self._users_per_page)
            pager = request.website.pager(url="/profile/users", total=user_count, page=page, step=self._users_per_page,
                                          scope=page_count if page_count < self._pager_max_pages else self._pager_max_pages)

            users = User.sudo().search(dom, limit=self._users_per_page, offset=pager['offset'],
                                       order='karma DESC, create_date DESC')
            user_values = self._prepare_all_users_values(users)

            values = {
                'users': user_values if not search_term and page == 1 else user_values,
                'pager': pager
            }
        else:
            values = {
                'users': [],
                'search': search_term,
                'pager': dict(page_count=0)
            }

        return request.render("website_profile.users_page_main", values)