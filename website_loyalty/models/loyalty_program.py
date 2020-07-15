# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, tools, _
from odoo import exceptions
from datetime import datetime


class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _description = 'Loyalty Program'

    def _get_name_of_program(self):
        text = 'LP for'
        text += ' ' + str(datetime.today().year) + '-' + str(datetime.today().year + 1)
        return text

    def _get_product_id(self):
        IrModelData = self.env['ir.model.data']
        return IrModelData.xmlid_to_res_id(
            'website_loyalty.product_loyalty_product') or False

    name = fields.Char(
        required=True,
        help="Unique name for each loyalty program.", default=_get_name_of_program)
    active = fields.Boolean('Active', default=True,
                            help="Untick if you want to deactive loyalty program.")
    loyalty_image = fields.Binary(
        'Loyalty Image', )
    description = fields.Text(
        string='Loyalty Program Description',
        help="Description for Loyalty Program")
    minimum_purchase = fields.Float(
        "Minimum Purchase Amount",
        required=True, default=1,
        help="Sale Order amount that have to satisfied by Customer to gain Loyalty Points.")
    purchase_amount = fields.Float("Amount of money spent",
                                   required=True, default=1,
                                   help="For example: \n for every purchase of 10 customer will get 1 earning point(s).")
    points_earn = fields.Float("Earning Point(s)",
                               required=True, default=1, help="Set Points that Customer will Earn as per the Amount Spent.")
    signup_points = fields.Float(
        "Sign Up Points", help='Set Sign Up Point for New Customer Sign Up',)
    redeem_stage = fields.Selection(
        selection=[
            ('confirm', 'Order Confirm'),
        ], string='Earn Stage On', default='confirm',
        help='Select on which Order Stage User will Gain Loyalty Point.')
    base_loyalty = fields.Selection(
        [('purchase', 'Purchase Amount')], 'Loyalty Points on basis of',
        readonly=True, default='purchase',)
    maximum_redeem_amount = fields.Float(
        "Maximum Redeem Points Per Sale Order", required=True, default=1.0,
        help="Maximum amount of money user can redeem at once.")
    redeem_type = fields.Selection(
        selection=[('one_time', 'One Time Redeem'),
                   ('partial_redeem', 'Partial Redeem')
                   ], string='Redeem Point Policy',
        required=True, default='partial_redeem', help='View Reedem Point Policy of customer.\
         \n One Time Redeem:Customer can redeem all his / her points at one time.\
          \n Partial Redeem:Customer can redeem only specific amount of points at a time.')
    product_id = fields.Many2one('product.template',
                                 domain=[('type', '=', 'service'), ],
                                 string="Loyalty Product", help="Select a Product which is to be given as a Loyalty Reward to the Customers")
    date_start = fields.Date(string='Start Date', help='Loyalty Program Start Date')
    date_end = fields.Date(string='End Date', help='Loyalty Program End Date')
    round_amount = fields.Boolean("Rounding Points?",
                                  help="Tick if you want to round loyalty points. If not tick it will use floating points calculation.")
    start_point = fields.Float("Point Start For Redeem", default=1.0,
                               help="Start point for redeem.")
    end_point = fields.Float("Point End For Redeem", default=50.0, help="End point for redeem.")
    reward = fields.Float('Discount Received',
                          required=True, default=1.0,
                          help="Enter how much amount for 1 point discounted to customer.")

    _sql_constraints = [
        ('unique_name', 'unique(name)',
         'A Loyalty Program name must be unique!'),
    ]

    @api.constrains('start_point', 'end_point')
    def _check_rule(self):
        if self.start_point <= 0.0:
            raise exceptions.ValidationError(_("Point Start For Redeem can not be less than 1."))
        if self.start_point == self.end_point:
            raise exceptions.ValidationError(
                _("Point Start For Redeem and Point End For Redeem is not same."))
        if self.start_point > self.end_point:
            raise exceptions.ValidationError(
                _("Point Start For Redeem must be less than Point End For Redeem."))

    @api.constrains('reward')
    def check_reward(self):
        if self.reward < 0:
            raise exceptions.ValidationError(
                _("Reward value %s can not be negative." % str(self.reward)))
        if self.reward == 0:
            raise exceptions.ValidationError(
                _("Reward value %s can not be zero." % str(self.reward)))

    # @api.one
    @api.constrains('points_earn')
    def check_earning(self):
        if self.points_earn < 0:
            raise exceptions.ValidationError(
                _("Earning value %s can not be negative." % str(self.points_earn)))
        if self.points_earn == 0:
            raise exceptions.ValidationError(
                _("Earning value %s can not be zero." % str(self.points_earn)))

    def get_loyatlty(self):
        # return loyatly object.
        search_obj = self.search([('date_start', '<=', fields.Date.context_today(self)),
                                  ('date_end', '>=', fields.Date.context_today(self)),
                                  ('active', '=', True)], limit=1)
        return search_obj

    def get_reward_points(self, WebsiteLoyalty, partner_points):
        reward = 0.0
        if WebsiteLoyalty.start_point <= partner_points and WebsiteLoyalty.end_point >= partner_points:
            reward = WebsiteLoyalty.reward
        return reward

    @api.constrains('date_start', 'date_end')
    def _check_date(self):
        if self.date_end < self.date_start:
            raise exceptions.ValidationError(_("End date can not be less than start date!!!"))
        if self.date_end == self.date_start:
            raise exceptions.ValidationError(_("Start date and End date can not be same!!!"))
        # if self.date_start < fields.Date.context_today(self):
        #    raise exceptions.ValidationError("Start date can not be less than today's date!!!")

    @api.constrains('maximum_redeem_amount')
    def _check_max_sale_amount(self):
        for obj in self:
            if obj.maximum_redeem_amount == 0 or obj.maximum_redeem_amount < 0:
                raise exceptions.ValidationError(
                    _("Maximum Redeem Amount Per Sale order can not be 0 or less than 0!!!"))

    @api.constrains('active')
    def _check_active_only_one(self):
        if len(self.search([('active', '=', True)])) > 1:
            raise exceptions.ValidationError(_("One Loyalty Program can be active at one time!"))

    @api.model
    def _signup_loyalty_program_points(self):
        #loyalty_program = self.sudo().search([('active', '=', True)], limit=1)
        loyalty_program = self.sudo().get_loyatlty()
        #self_obj = self.sudo().get_loyatlty()
        return loyalty_program and loyalty_program.signup_points or False

    @api.model
    def _get_sale_line_info(self):
        return {'img': self.loyalty_image, 'name': self.name, 'description': self.description}

    @api.model
    def update_partner_loyalty(self, order_obj, order_state):
        if self.redeem_stage == order_state:
            order_obj.partner_id.loyalty_points = order_obj.partner_id.loyalty_points + order_obj.loyalty_points
            order_obj.write({'loyalty_state': 'done'})
            return self._create_gain_history(order_obj)

    def _create_gain_history(self, sale_order):
        self.ensure_one()
        already_deducted = self.env['loyalty.history'].sudo().search_count(
            [('sale_order_id', '=', sale_order.id),
             ('loyalty_process', '=', 'addition')])
        if not already_deducted:
            history_create_val = {
                'ref': 'Sale Order',
                'loyalty_id': self.id,
                'points_processed': sale_order.loyalty_points,
                'sale_order_id': sale_order.id,
                'loyalty_process': 'addition',
                'partner_id': sale_order.partner_id.id,
                'redeem_type': self.redeem_type,
            }
            return self.env['loyalty.history'].sudo().create(history_create_val)

    def _create_redeem_history(self, sale_order, state='save'):
        self.ensure_one()
        order_line_ids = [ids for ids in sale_order.website_order_line]
        already_deducted = self.env['loyalty.history'].sudo().search_count(
            [('sale_order_id', '=', sale_order.id),
             ('loyalty_process', '=', 'deduction')])
        for order_line_id in order_line_ids:
            if not already_deducted and state == 'save' and order_line_id.is_virtual:
                vals = {
                    'ref': 'Sale Order',
                    'loyalty_id': self.id,
                    'loyalty_process': 'deduction',
                    'points_processed': order_line_id.redeem_points,
                    'redeem_amount': order_line_id.price_unit,
                    'sale_order_id': order_line_id.order_id.id,
                    'partner_id': order_line_id.order_partner_id.id,
                    'redeem_type': self.redeem_type,
                }
                return self.env['loyalty.history'].sudo().create(vals)

    @api.model
    def get_loyalty_points_count(self, amount):
        #self_obj = self.sudo().search([('active', '=', True)], limit=1)
        self_obj = self.sudo().get_loyatlty()
        loyalty_points = 0.0
        if not self_obj:
            return loyalty_points
        if self_obj.purchase_amount and amount >= self_obj.minimum_purchase:
            offer_ratio = (self_obj.points_earn or 0.0) / (self_obj.purchase_amount or 0.0)
            if self_obj.round_amount:
                loyalty_points = round((offer_ratio or 0.0) * (amount or 0.0))
            else:
                loyalty_points = (offer_ratio or 0.0) * (amount or 0.0)
            return loyalty_points
        else:
            return loyalty_points

    def cancel_redeem_history(self, sale_obj):
        loyalty_history_objs = self.env['loyalty.history'].sudo().search(
            [('sale_order_id', '=', sale_obj.id)])
        add = 0.0
        deduct = 0.0
        for history_obj in loyalty_history_objs:
            if history_obj.loyalty_process == 'deduction':
                deduct = history_obj.points_processed
            elif history_obj.loyalty_process == 'addition':
                add = history_obj.points_processed
        if sale_obj.loyalty_state != 'cancel' and loyalty_history_objs:
            points = deduct if sale_obj.loyalty_state == 'draft' else (deduct - add)
            sale_obj.partner_id.loyalty_points += points
            loyalty_history_objs.sudo().write({'loyalty_process': 'cancel'})
            sale_obj.loyalty_state = 'cancel'


LoyaltyProgram()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
