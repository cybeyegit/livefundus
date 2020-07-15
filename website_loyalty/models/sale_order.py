# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

import logging
import random

from odoo import api, fields, models, tools, _
from odoo import exceptions
from datetime import datetime
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import odoo.addons.decimal_precision as dp
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.price_total', 'extra_loyalty_points')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        loyalty_program_pool = self.env['loyalty.program']
        super(SaleOrder, self)._amount_all()
        for order in self:
            if order.loyalty_state not in ['done', 'cancel']:
                order.update({'loyalty_points': order.extra_loyalty_points +
                              loyalty_program_pool.get_loyalty_points_count(order.amount_total)})

    loyalty_state = fields.Selection(
        selection=[('draft', 'Draft'),
                   ('done', 'Done'),
                   ('cancel', 'Cancel'),
                   ], string='Loylaty State',
        help='Stage of the Loyalty Points.', default='draft', )
    # amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    loyalty_points = fields.Float(
        string='Loyalty Points', store=True, readonly=True, compute='_amount_all', digits='Discount')
    extra_loyalty_points = fields.Float('Extra Loyalty Points',)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        loyalty_pool = self.env['loyalty.program']
        #loyalty_obj = loyalty_pool.search([('active', '=', True)], limit=1)
        loyalty_obj = loyalty_pool.get_loyatlty()
        if not loyalty_obj:
            return res
        for sale_obj in self:
            if sale_obj.loyalty_points:
                loyalty_obj.update_partner_loyalty(sale_obj, 'confirm')
            '''
            search_so_line = self.env['sale.order.line'].search(
                [('is_virtual', '=', True),
                 ('product_id', '=', False)])
            if search_so_line:
                search_so_line.write({'invoice_status': 'no'})
            '''
        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        loyalty_pool = self.env['loyalty.program']
        #loyalty_obj = loyalty_pool.search([('active', '=', True)], limit=1)
        loyalty_obj = loyalty_pool.sudo().get_loyatlty()
        if not loyalty_obj:
            return res
        for sale_obj in self:
            loyalty_obj.cancel_redeem_history(sale_obj)
        return res

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        loyalty_prod_id = False
        loyalty_obj = False
        loyalty_obj = self.env['loyalty.program'].sudo().get_loyatlty()
        loyalty_prod_id = loyalty_obj and loyalty_obj.product_id.product_variant_ids.id or False
        self.ensure_one()
        SaleOrderLineSudo = self.env['sale.order.line'].sudo()

        try:
            if add_qty:
                add_qty = float(add_qty)
        except ValueError:
            add_qty = 1
        try:
            if set_qty:
                set_qty = float(set_qty)
        except ValueError:
            set_qty = 0
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(
                _('It is forbidden to modify a sales order which is not in draft status.'))
        if line_id is not False:
            order_lines = self._cart_find_product_line(product_id, line_id, **kwargs)
            order_line = order_lines and order_lines[0]

        # Create line if no line with product_id can be located
        if not order_line:
            values = self._website_product_id_change(self.id, product_id, qty=1)

            custom_values = kwargs.get('product_custom_attribute_values')
            if custom_values:
                values['product_custom_attribute_value_ids'] = [(0, 0, {
                    'attribute_value_id': custom_value['attribute_value_id'],
                    'custom_value': custom_value['custom_value']
                }) for custom_value in custom_values]

            no_variant_attribute_values = kwargs.get('no_variant_attribute_values')
            if no_variant_attribute_values:
                values['product_no_variant_attribute_value_ids'] = [
                    (6, 0, [int(attribute['value']) for attribute in no_variant_attribute_values])
                ]

            product_context = dict(self.env.context)
            product_context.setdefault('lang', self.sudo().partner_id.lang)
            product_with_context = self.env['product.product'].with_context(product_context)
            product = product_with_context.browse(int(product_id))
            no_variant_attribute_values = kwargs.get('no_variant_attribute_values') or []
            received_no_variant_values = product.env['product.template.attribute.value'].browse([int(ptav['value']) for ptav in no_variant_attribute_values])
            received_combination = product.product_template_attribute_value_ids | received_no_variant_values
            product_template = product.product_tmpl_id

            combination = product_template._get_closest_possible_combination(received_combination)
            product = product_template._create_product_variant(combination)
            custom_values = kwargs.get('product_custom_attribute_values') or []
            received_custom_values = product.env['product.template.attribute.value'].browse([int(ptav['custom_product_template_attribute_value_id']) for ptav in custom_values])

            for ptav in combination.filtered(lambda ptav: ptav.is_custom and ptav not in received_custom_values):
                custom_values.append({
                    'custom_product_template_attribute_value_id': ptav.id,
                    'custom_value': '',
                })

            # save is_custom attributes values
            if custom_values:
                values['product_custom_attribute_value_ids'] = [(0, 0, {
                    'custom_product_template_attribute_value_id': custom_value['custom_product_template_attribute_value_id'],
                    'custom_value': custom_value['custom_value']
                }) for custom_value in custom_values]
            # create the line
            order_line = SaleOrderLineSudo.create(values)

            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))
            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.product_uom_qty + (add_qty or 0)

        # Remove zero of negative lines
        if quantity <= 0:
            order_line.unlink()
        else:
            # update line
            if loyalty_prod_id != product_id:
                values = self._website_product_id_change(self.id, product_id, qty=quantity)
                if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
                    order = self.sudo().browse(self.id)
                    product_context = dict(self.env.context)
                    product_context.setdefault('lang', order.partner_id.lang)
                    product_context.update({
                        'partner': order.partner_id.id,
                        'quantity': quantity,
                        'date': order.date_order,
                        'pricelist': order.pricelist_id.id,
                    })
                    product = self.env['product.product'].with_context(
                        product_context).browse(product_id)
                    values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                        order_line._get_display_price(product),
                        order_line.product_id.taxes_id,
                        order_line.tax_id,
                        self.company_id
                    )

                order_line.write(values)

        # link a product to the sales order
        if kwargs.get('linked_line_id'):
            linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
            order_line.write({
                'linked_line_id': linked_line.id,
                'name': order_line.name + "\n" + _("Option for:") + ' ' + linked_line.product_id.display_name,
            })
            linked_line.write({"name": linked_line.name + "\n" + _("Option:") +
                               ' ' + order_line.product_id.display_name})

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == order_line.id)
        for option_line_id in option_lines:
            self._cart_update(option_line_id.product_id.id,
                              option_line_id.id, add_qty, set_qty, **kwargs)
        return {'line_id': order_line.id, 'quantity': quantity, 'option_ids': list(set(option_lines.ids))}

    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        for order in self:
            group_key = order.id if grouped else (
                order.partner_invoice_id.id, order.currency_id.id)
            for line in order.order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = order
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if order.name not in invoices[group_key].origin.split(', '):
                        vals['origin'] = invoices[group_key].origin + ', ' + order.name
                    if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', ') and order.client_order_ref != invoices[group_key].name:
                        vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
                    invoices[group_key].write(vals)
                if line.qty_to_invoice > 0:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
                elif line.qty_to_invoice < 0 and final:
                    line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)

            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoice] = references[invoice] | order

        if not invoices:
            raise UserError(_('There is no invoicable line.'))

        for invoice in list(invoices.values()):
            if not invoice.invoice_line_ids:
                raise UserError(_('There is no invoicable line.'))
            # customisation for the loyalty module
            IrModelData = self.env['ir.model.data']
            product_id = IrModelData.xmlid_to_res_id(
                'website_loyalty.product_loyalty_product') or False
            # ENd
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_untaxed < 0:
                for line in invoice.invoice_line_ids:
                  # customisation for the loyalty module
                    if product_id == line.product_id.id:
                        line.quantity = line.quantity
                    else:
                        line.quantity = -line.quantity
                        invoice.type = 'out_refund'
                # ENd
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view('mail.message_origin_link',
                                           values={'self': invoice, 'origin': references[invoice]},
                                           subtype_id=self.env.ref('mail.mt_note').id)
        return [inv.id for inv in list(invoices.values())]


SaleOrder()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    '''
    @api.depends('state', 'product_uom_qty', 'qty_delivered', 'qty_to_invoice', 'qty_invoiced')
    def _compute_invoice_status(self):

        """
        Compute the invoice status of a SO line. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also hte default value if the conditions of no other status is met.
        - to invoice: we refer to the quantity to invoice of the line. Refer to method
          `_get_to_invoice_qty()` for more information on how this quantity is calculated.
        - upselling: this is possible only for a product invoiced on ordered quantities for which
          we delivered more than expected. The could arise if, for example, a project took more
          time than expected but we decided not to invoice the extra cost to the client. This
          occurs onyl in state 'sale', so that when a SO is set to done, the upselling opportunity
          is removed from the list.
        - invoiced: the quantity invoiced is larger or equal to the quantity ordered.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.state not in ('sale', 'done'):
                line.invoice_status = 'no'
            elif not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                line.invoice_status = 'to invoice'
            elif line.state == 'sale' and line.product_id.invoice_policy == 'order' and\
                    float_compare(line.qty_delivered, line.product_uom_qty, precision_digits=precision) == 1:
                line.invoice_status = 'upselling'
            elif float_compare(line.qty_invoiced, line.product_uom_qty, precision_digits=precision) >= 0:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'
            if not line.product_id and line.invoice_lines:
                line.invoice_status = 'invoiced'
    '''
    '''

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            if line.order_id.state in ['sale', 'done']:
                if line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
            if not line.product_id and line.is_virtual:
                line.qty_to_invoice = 1.0
    '''

    is_virtual = fields.Boolean('Virtual Product')
    redeem_points = fields.Float('Redeem Virtual Points')
    reward_amount = fields.Float('Redeem Amount')
    image = fields.Binary("Product Image for virtual",)

    '''
    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        res = {}
        account = self.product_id.property_account_income_id or self.product_id.categ_id.property_account_income_categ_id
        if not account and not self.product_id:
            category_id = self.env['product.category'].search(
                                 [('property_account_expense_categ_id', '!=', False),
                                  ], limit=1)
            account = category_id and category_id.property_account_expense_categ_id or False
            if not account:
                raise UserError(_('Please define Expense Account in any product category.'))
        if not account:
            raise UserError(_('Please define income account for this product: "%s" (id:%d) - or for its category: "%s".') %
                (self.product_id.name, self.product_id.id, self.product_id.categ_id.name))

        fpos = self.order_id.fiscal_position_id or self.order_id.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)

        res = {
            'name': self.name,
            'sequence': self.sequence,
            'origin': self.order_id.name,
            'account_id': account.id,
            'price_unit': self.price_unit,
            'quantity': qty,
            'discount': self.discount,
            'uom_id': self.product_uom.id,
            'product_id': self.product_id.id or False,
            'layout_category_id': self.layout_category_id and self.layout_category_id.id or False,
            'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
            'account_analytic_id': self.order_id.project_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
        }
        return res
        '''


SaleOrderLine()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
