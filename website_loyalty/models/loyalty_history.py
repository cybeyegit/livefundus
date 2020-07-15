# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo import exceptions


class LoyaltyHistory(models.Model):
    _name = 'loyalty.history'
    _description = 'Loyalty History'
    _rec_name = 'sale_order_id'
    _order = 'id desc'

    sale_order_id = fields.Many2one(
        comodel_name='sale.order', string='Sale Order Number',
        help='Sale Order Number', ondelete='restrict',)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer', help='Customer Name')
    redeem_amount = fields.Float(
        string='Discount Amount',
        help='Discount Offered to customer')
    points_processed = fields.Float(string="Points Processed",
                                    help="Points processed during loyalty program")
    loyalty_process = fields.Selection(
        selection=[('addition', 'Points Added'),
                   ('deduction', 'Point Deducted'),
                   ('cancel', 'Cancelled'),
                   ],
        string="Process")
    loyalty_id = fields.Many2one(
        comodel_name='loyalty.program', string='Loyalty Program', required=True,)
    #redeem_type = fields.Selection(related='loyalty_id.redeem_type')
    redeem_type = fields.Selection(
        selection=[('one_time', 'One Time Redeem'),
                   ('partial_redeem', 'Partial Redeem')
                   ], string='Redeem Point Policy',
        required=True, help='View Reedem Point Policy of customer.\
         \n One Time Redeem:Customer can redeem all his / her points at one time.\
          \n Partial Redeem:Customer can redeem only specific amount of points at a time.')
    ref = fields.Char(string="Description", help="Description for Loyalty Program")
    date = fields.Date(
        string='Redeemed Date', default=fields.Date.context_today,
        help='Redeemed Date')

    def unlink(self):
        raise exceptions.UserError(_('Sorry, Currently you cannot delete Loyalty History!'))
        return super(LoyaltyHistory, self).unlink()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
