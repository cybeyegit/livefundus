# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, tools, _
from odoo import exceptions
from datetime import datetime
import odoo.addons.decimal_precision as dp


class ResPartner(models.Model):
    _inherit = 'res.partner'

    loyalty_points = fields.Float(
        'Loyalty Points', help='The sum of loyalty points!', digits='Discount')

    def view_history(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Loyalty History For ') + self.name,
            'res_model': 'loyalty.history',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'domain': ['|', ('partner_id', '=', self.id),
                       ('partner_id', 'child_of', self.id)],
            'target': 'current',
            'context': self._context
        }


ResPartner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
