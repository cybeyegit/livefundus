# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo import exceptions
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    def get_with_currency(self, amount):
        currency_id = request.website.pricelist_id.currency_id
        return ' ' + currency_id.symbol + ' ' + str(round(amount or 0, 2)) if currency_id.position != 'after' else str(round(amount or 0, 2)) + ' ' + currency_id.symbol + ' '

    def get_rewards(self, sale_order_amount):
        res = self._get_loyalty_amount(sale_order_amount)
        redeem_points = res['redeem_point']
        self.sale_get_order().partner_id.loyalty_points = res['remain_points']
        result = {'reward_amount': res['reward_amount']}
        # loyalty_program_obj = self.env['loyalty.program'].sudo().search(
        #   [('active', '=', True)], limit=1)
        loyalty_program_obj = self.env['loyalty.program'].sudo().get_loyatlty()
        IrModelData = self.env['ir.model.data']

        uom_id = IrModelData.xmlid_to_res_id(
            'product.product_uom_unit') or False
        if not uom_id:
            uom_id = self.env['uom.uom'].sudo().search([], limit=1)
            uom_id = uom_id and uom_id.id or False
        if loyalty_program_obj.product_id:
            self.env['sale.order.line'].sudo().create({
                'order_id': self.sale_get_order().id,
                'product_id': loyalty_program_obj.product_id.product_variant_ids.id,
                'price_unit': -result['reward_amount'],
                'redeem_points': redeem_points,
                'is_virtual': True,
                'product_uom': uom_id,
                'name': (loyalty_program_obj.product_id.product_variant_ids.name or '') + '  \n' + (loyalty_program_obj.product_id.product_variant_ids.description_sale or ''), })

        return result

    def _get_loyalty_amount(self, sale_order_amount):
        result = {'reward_amount': 0.0,
                  'remain_points': 0.0, 'redeem_point': 0.0}
        self.ensure_one()
        if sale_order_amount > 1:
            # loyalty_program_obj = self.env['loyalty.program'].sudo().search(
            #    [('active', '=', True)], limit=1)
            loyalty_program_obj = self.env['loyalty.program'].sudo(
            ).get_loyatlty()
            user_obj = self.env['res.users'].sudo().browse([(self._uid)])
            maximum_redeem_amount = loyalty_program_obj.maximum_redeem_amount
            redeem_rule = 0.0
            if loyalty_program_obj.start_point <= user_obj.partner_id.loyalty_points and loyalty_program_obj.end_point >= user_obj.partner_id.loyalty_points:
                redeem_rule = loyalty_program_obj.reward
            else:
                redeem_rule = 0.0
            #computed_redeem_amount = user_obj.partner_id.loyalty_points * redeem_rule.reward
            computed_redeem_amount = user_obj.partner_id.loyalty_points * redeem_rule
            reduction_amount = computed_redeem_amount if computed_redeem_amount < maximum_redeem_amount else maximum_redeem_amount
            if loyalty_program_obj.redeem_type == 'one_time':
                if sale_order_amount <= reduction_amount:
                    if loyalty_program_obj.round_amount:
                        result['reward_amount'] = round(sale_order_amount)
                    else:
                        result['reward_amount'] = sale_order_amount
                else:
                    if loyalty_program_obj.round_amount:
                        result['reward_amount'] = round(reduction_amount)
                    else:
                        result['reward_amount'] = reduction_amount
                result['remain_points'] = 0
                result['redeem_point'] = user_obj.partner_id.loyalty_points
            # elif loyalty_program_obj.redeem_type == 'partial_redeem' and redeem_rule.reward:
            elif loyalty_program_obj.redeem_type == 'partial_redeem' and redeem_rule:
                if sale_order_amount <= reduction_amount:
                    if loyalty_program_obj.round_amount:
                        result['reward_amount'] = round(sale_order_amount)
                        #result['remain_points'] = round(abs((computed_redeem_amount-sale_order_amount) / redeem_rule.reward))
                        result['remain_points'] = round(
                            abs((computed_redeem_amount-sale_order_amount) / redeem_rule))
                        #result['redeem_point'] = round(sale_order_amount / redeem_rule.reward)
                        result['redeem_point'] = round(
                            sale_order_amount / redeem_rule)
                    else:
                        # # if not rounding option is selected
                        result['reward_amount'] = sale_order_amount
                        #result['remain_points'] = abs((computed_redeem_amount-sale_order_amount) / redeem_rule.reward)
                        result['remain_points'] = abs(
                            (computed_redeem_amount-sale_order_amount) / redeem_rule)
                        #result['redeem_point'] = sale_order_amount / redeem_rule.reward
                        result['redeem_point'] = sale_order_amount / redeem_rule
                else:
                    if loyalty_program_obj.round_amount:
                        result['reward_amount'] = round(reduction_amount)
                        #result['remain_points'] = round(abs((computed_redeem_amount-reduction_amount) / redeem_rule.reward))
                        result['remain_points'] = round(
                            abs((computed_redeem_amount-reduction_amount) / redeem_rule))
                        #result['redeem_point'] = round(reduction_amount / redeem_rule.reward)
                        result['redeem_point'] = round(
                            reduction_amount / redeem_rule)
                    else:
                        # # if not rounding option is selected
                        result['reward_amount'] = reduction_amount
                        #result['remain_points'] = abs((computed_redeem_amount-reduction_amount) / redeem_rule.reward)
                        result['remain_points'] = abs(
                            (computed_redeem_amount - reduction_amount) / redeem_rule)
                        #result['redeem_point'] = reduction_amount / redeem_rule.reward
                        result['redeem_point'] = reduction_amount / redeem_rule
        return result

    def get_virtual_image(self):
        # loyalty_program_obj = self.env['loyalty.program'].sudo().search(
        #    [('active', '=', True)], limit=1)
        loyalty_program_obj = self.env['loyalty.program'].sudo().get_loyatlty()
        return loyalty_program_obj


    def get_loyalty_product(self):
        self.ensure_one()
        # return self.env['loyalty.program'].sudo().search([('active', '=', True)], limit=1)
        return self.env['loyalty.program'].sudo().get_loyatlty()


Website()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
