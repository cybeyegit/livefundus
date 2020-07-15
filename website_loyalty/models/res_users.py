# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo import exceptions
from datetime import datetime


class ResUsers(models.Model):
    _inherit = 'res.users'

    loyalty_points = fields.Float(
        string='Loyalty Points', related='partner_id.loyalty_points')

    @api.model
    def create(self, vals):
        loyalty_prog_pool = self.env['loyalty.program']
        IrModelData = self.env['ir.model.data']
        #loyalty_prog_obj = loyalty_prog_pool.search([('active', '=', True)], limit=1)
        loyalty_prog_obj = loyalty_prog_pool.get_loyatlty()
        group_id = IrModelData.xmlid_to_res_id(
            'base.group_portal') or False
        if vals.get('in_group_1') and vals['in_group_1'] is not False \
           or vals.get('groups_id') and vals['groups_id'][0][2] and vals['groups_id'][0][2][2] == group_id \
           and len(loyalty_prog_obj) != 0:
            sign_up_loyalty_point = loyalty_prog_obj._signup_loyalty_program_points() or 0.0
            res = super(ResUsers, self).create(vals)
            res.partner_id.sudo().write(
                {'loyalty_points': sign_up_loyalty_point})
            #self._cr.execute('update res_partner set loyalty_points = %s where id = %s' %(str(loyalty_prog_obj._signup_loyalty_program_points()), str(res.id)))
            history_create_val = {
                'points_processed': loyalty_prog_obj._signup_loyalty_program_points(),
                'partner_id': res.partner_id.id,
                'loyalty_id': loyalty_prog_obj.id,
                'loyalty_process': 'addition',
                'ref': 'SignUp',
                'redeem_type': loyalty_prog_obj.redeem_type,
            }
            create_id = self.env['loyalty.history'].create(history_create_val)
            return res
        return super(ResUsers, self).create(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
