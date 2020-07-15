# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.website_sale.controllers.main import WebsiteSale


MSG_NO_Redeem_Points = _("<b>Sorry You have 0 Points. You can't redeem right now.</b>")
MSG_Redeem_NO_Rule_Reward = _('<b>Currently no redeem  reward rule is available, \
                               Please try later !</b>')
MSG_Redeem_Once = _('<b>As per Redeem policy, You are allowed to \
                        redeem only  once per sale order which you have \
                        already redeemed !</b>')
MSG_Error_NO_Redeem_Rule = _('<b>Sorry currently no  redeem policy  is available, \
                            Please try later !</b>')
MSG_Error_Loyalty_Program = _('<b>Sorry loyalty  feature is not available \
                                   right now , Please try later for loyalty program!</b>')


class WebsiteLoyalty(http.Controller):

    @http.route(['/myloyality/confimation/'], type='json', auth="public", website=True)
    def get_confimation(self, **post):
        """
        This Method is called on the  click of Redeem Reward link available on cart page,
        It validate all the conditions like
            # loyalty_program have no object,
            # minimum Purchase amount criteria of loyalty_program.
            #   have no object
            # user is not login,
            # point_start ['start points'] criteria of redeem_rule
        """
        values = {'allowed_redeem': False, 'message': '', 'loginfirst': False}
        cr, uid = request.cr, request.uid
        res_user_obj = request.env['res.users'].sudo().browse(uid)
        ir_model_data = request.env['ir.model.data']
        p_user_id = ir_model_data.get_object_reference('base', 'public_user')[1]
        # loyalty_program = request.env['loyalty.program'].sudo().search(
        #    [('active', '=', True)], limit=1)
        loyalty_program = request.env['loyalty.program'].sudo().get_loyatlty()
        currency_symbol = request.website.pricelist_id.currency_id.symbol
        website = request.website
        if request.session.get('reward') == 'Taken':
            values['message'] = MSG_Redeem_Once
        else:
            if uid == p_user_id:
                values['loginfirst'] = True
            else:
                if len(loyalty_program) == 0:
                    values['message'] = MSG_Error_Loyalty_Program
                else:
                    if not request.website.sale_get_order() or not request.website.sale_get_order().amount_total:
                        values['message'] = _('<b>Your cart is empty !</b>')
                    else:
                        sale_order_amount = request.website.sale_get_order().amount_total
                        if sale_order_amount < loyalty_program.minimum_purchase:
                            values['message'] = _(
                                'Your Purchase amount ' + website.get_with_currency(sale_order_amount) + ' is \
                                not satisfying the <b> minimum Purchase amount criteria </b> You have to make at least \
                                ' + website.get_with_currency(loyalty_program.minimum_purchase)+' amount of purchase to  start claiming your reward.\n')

                        else:
                            users_loyalty_points = res_user_obj.partner_id.loyalty_points
                            if not users_loyalty_points:
                                values['message'] = MSG_NO_Redeem_Points
                            else:
                                # if not loyalty_program.redeem_rule_ids:
                                if not loyalty_program.reward:
                                    values['message'] = MSG_Error_NO_Redeem_Rule
                                else:
                                    redeem_rule = 0.0
                                    if loyalty_program.start_point <= users_loyalty_points and loyalty_program.end_point >= users_loyalty_points:
                                        redeem_rule = loyalty_program.reward
                                    # if len(redeem_rule) == 0:
                                    if not redeem_rule:
                                        values['message'] = _("<b>Your Points " + str(
                                            users_loyalty_points) + " not lie in the point range of any Redeem Policy,Please try later!</b>")
                                    else:
                                        # if res_user_obj.partner_id.loyalty_points <
                                        # redeem_rule.start_point:
                                        if res_user_obj.partner_id.loyalty_points < redeem_rule:
                                            values['message'] = _(
                                                '<b>Sorry. Your point '+str(res_user_obj.partner_id.loyalty_points)+' \
                                                does not lie in the point range of our Redemption Policy. You need at least '
                                                + str(redeem_rule.start_point) + 'points to start claiming your reward. </b>')
                                        else:
                                            reward = redeem_rule
                                            if not reward:
                                                values['message'] = MSG_Redeem_NO_Rule_Reward
                                            else:
                                                values = self._allowed_redeem(
                                                    cr, uid, res_user_obj, loyalty_program, redeem_rule,
                                                    values, currency_symbol)
        value = {}
        value['website_loyalty.test_template_bc'] = request.env['ir.ui.view'].render_template("website_loyalty.test_template_bc",
                                                                                              values)
        return value['website_loyalty.test_template_bc']

    def _allowed_redeem(self, cr, uid, user_obj, loyalty_program, redeem_rule, values, currency_symbol):
        """
        Input Parameter : cr,udi,user_obj,loyalty_program_obj
        Return allowed_redeem = True in a dictionary  with the appropriate message

        This Method is helping method  get_confimation ,
        which is called by the /myloyality/confimation/ Before calling get_reward
        It set message in the dictionary according to redeem_type !
        """
        website = request.website
        reward = redeem_rule
        computed_redeem_amount = user_obj.partner_id.loyalty_points * reward
        maximum_redeem_amount = loyalty_program.maximum_redeem_amount
        sale_order_amount = request.website.sale_get_order().amount_total

        reduction_amount = computed_redeem_amount if computed_redeem_amount < maximum_redeem_amount else maximum_redeem_amount
        final_reduced_amount = sale_order_amount if sale_order_amount < reduction_amount else reduction_amount
        diff = sale_order_amount if sale_order_amount < reduction_amount else reduction_amount

        if loyalty_program.redeem_type == 'partial_redeem' and reward:
            values['message'] = _(
                'As per <b> Partial Redemption policy </b> ' + str(final_reduced_amount / reward) + ' \
                points worth of  ' + website.get_with_currency(final_reduced_amount) + '\
                amounts will be spent from your account!')
            values['allowed_redeem'] = True

        else:
            if loyalty_program.redeem_type == 'one_time':
                percent_benefit = round((diff * 100 / reduction_amount), 2)
                if percent_benefit < 100:
                    values['message'] = _(' As Per <b> One Time Redemption policy </b> you will enjoy only ' + str(
                        percent_benefit) + '% \nBenefits on this redemption of ' + website.get_with_currency(final_reduced_amount) + '!')
                else:
                    values['message'] = _('<b> Congratulations !</b><br/> You are spending 100% \n  of your reward points ' +
                                          website.get_with_currency(final_reduced_amount) + '.')
                values['allowed_redeem'] = True
        return values

    @http.route(['/loyality/get_reward/'], type='http', auth="public", website=True)
    def get_reward(self, **post):
        """
        Input Parameter : None
        return Redirect To Cart Page Of User

        This Method is called after the get_confimation,
        It task Is just to call get_rewards  Method(custom) of website model
        """
        result = request.website.get_rewards(request.website.sale_get_order().amount_total)
        if result.get('reward_amount'):
            request.session['reward'] = 'Taken'
        return request.redirect("/shop/cart/")


class WebsiteSaleInherit(WebsiteSale):

    @http.route('/shop/payment/get_status/<int:sale_order_id>', type='json', auth="public", website=True)
    def payment_get_status(self, sale_order_id, **post):
        res_super = super(WebsiteSaleInherit, self).payment_get_status(sale_order_id)
        order = request.env['sale.order'].sudo().browse(sale_order_id)
        if order.state in ['sent', 'sale', 'done']:
            # loyalty_program = request.env['loyalty.program'].sudo().search(
            #    [('active', '=', True)], limit=1)
            loyalty_program = request.env['loyalty.program'].sudo().get_loyatlty()
            if len(loyalty_program) != 0:
                loyalty_program.update_partner_loyalty(
                    order, 'draft')
                loyalty_program._create_redeem_history(order)
        request.session['reward'] = ''
        return res_super


class WebsiteVirtualProduct(http.Controller):

    @http.route(['/remove/virtualproduct/<temp>'], type='http', auth="public", website=True)
    def virtual_product_remove(self, temp):
        virtual_product_sale_order_line = request.env['sale.order.line'].sudo().search(
            [('id', '=', temp),
             ])
        request.website.sale_get_order().partner_id.loyalty_points += virtual_product_sale_order_line.redeem_points
        virtual_product_sale_order_line.unlink()
        request.session['reward'] = ''
        return request.redirect("/shop/cart/")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
