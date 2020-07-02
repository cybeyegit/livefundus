# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.http import request

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
