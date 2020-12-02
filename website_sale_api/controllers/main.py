# -*- coding: utf-8 -*-

from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo.osv import expression
from .serialization import serialize_order, serialize_products, serialize_categories
from odoo.addons.payment.controllers.portal import PaymentProcessing

class WebsiteSaleAPI(WebsiteSale):

    @staticmethod
    def _get_api_search_domain(search, category, attrib_values, search_in_description=True):
        domains = [[("sale_ok", "=", True)]]
        if search:
            for srch in search.split(" "):
                subdomains = [
                    [('name', 'ilike', srch)],
                    [('product_variant_ids.default_code', 'ilike', srch)]
                ]
                if search_in_description:
                    subdomains.append([('description', 'ilike', srch)])
                    subdomains.append([('description_sale', 'ilike', srch)])
                domains.append(expression.OR(subdomains))

        if category:
            domains.append([('public_categ_ids', 'child_of', int(category))])

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domains.append([('attribute_line_ids.value_ids', 'in', ids)])
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domains.append([('attribute_line_ids.value_ids', 'in', ids)])

        return expression.AND(domains)

    @http.route('/shop/api/products', type='json', auth='public', website=True)
    def api_products(self, page=0, category=None, search='', ppg=20, **post):
        Category = request.env['product.public.category'].sudo()
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
        else:
            category = Category

        domain = self._get_api_search_domain(search, category, [])
        # print(domain)
        # pricelist_context, pricelist = self._get_pricelist_context()
        # request.context = dict(request.context, pricelist=pricelist.id, partner=request.env.user.partner_id)

        if search:
            post["search"] = search

        Product = request.env['product.template'].with_context(bin_size=True).sudo()

        search_product = Product.search(domain)

        product_count = len(search_product)
        # pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        products = Product.search(domain, limit=ppg, offset=ppg * page, order=self._get_search_order(post))

        ProductAttribute = request.env['product.attribute']
        attributes = ProductAttribute.search([('product_tmpl_ids', 'in', search_product.ids)])

        # layout_mode = request.session.get('website_sale_shop_layout_mode')
        # if not layout_mode:
        #     if request.website.viewref('website_sale.products_list_view').active:
        #         layout_mode = 'list'
        #     else:
        #         layout_mode = 'grid'

        values = {
            'search': search,
            # 'category': category.read(),
            # 'pricelist': pricelist.read(),
            'products': serialize_products(products, max_depth=1),
            'search_count': product_count,  # common for all searchbox
            'ppg': ppg,
            # 'categories': categs.read(),
            'attributes': attributes.read(),

        }

        return values

    @http.route('/shop/api/product', type='json', auth='public', website=True)
    def api_product(self, product_id=None, **post):
        Product = request.env['product.template'].sudo()
        return serialize_products(Product.browse(product_id))

    @http.route('/shop/api/categories', type='json', auth='public', website=True)
    def api_categories(self, categ_ids=None, **post):
        if categ_ids is None:
            categ_ids = []

        Category = request.env['product.public.category'].sudo()
        categs_domain = [('parent_id', '=', False)]

        if categ_ids:
            categs_domain.append(('id', 'in', categ_ids))

        categs = Category.search(categs_domain)

        values = {
            'categories': serialize_categories(categs)
        }

        return values

    @http.route(['/shop/api/cart/update'], type='json', auth="public", methods=['POST'], website=True)
    def api_cart_update(self, product_id, line_id=None, add_qty=None, set_qty=None, ):
        """This route is called when changing quantity from the cart or adding
        a product from the wishlist."""
        order = request.website.sale_get_order(force_create=1)
        if order.state != 'draft':
            request.website.sale_reset()
            return {}

        order._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty)
        if not order.cart_quantity:
            request.website.sale_reset()

        order = request.website.sale_get_order()

        return serialize_order(order)

    @http.route(['/shop/api/cart'], type='json', auth="public", methods=['POST'], website=True)
    def api_cart(self, **post):
        order = request.website.sale_get_order()
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()

        return serialize_order(order)

    @http.route(['/shop/api/address'], type='json', methods=['POST'], auth="public", website=True)
    def api_address(self, **kw):
        Partner = request.env['res.partner'].with_context(show_address=1).sudo()
        order = request.website.sale_get_order()
        partner_id = int(kw.get('partner_id', -1))

        # IF PUBLIC ORDER
        if order.partner_id.id == request.website.user_id.sudo().partner_id.id:
            # Create Billing
            mode = ('new', 'billing')

        # IF ORDER LINKED TO A PARTNER
        else:
            if partner_id > 0:
                if partner_id == order.partner_id.id:
                    # Edit billing
                    mode = ('edit', 'billing')
                else:
                    # Edit Shipping
                    shippings = Partner.search([('id', 'child_of', order.partner_id.commercial_partner_id.ids)])
                    if partner_id in shippings.mapped('id'):
                        mode = ('edit', 'shipping')
                    else:
                        return Forbidden()

            elif partner_id == -1:
                # Create Shipping
                mode = ('new', 'shipping')

            else:  # no mode - refresh without post?
                return NotFound()

        # IF POSTED
        if 'submitted' in kw:
            pre_values = self.values_preprocess(order, mode, kw)
            errors, error_msg = self.checkout_form_validate(mode, kw, pre_values)
            post, errors, error_msg = self.values_postprocess(order, mode, pre_values, errors, error_msg)

            if errors:
                return Forbidden(error_msg)
            else:
                partner_id = self._checkout_form_save(mode, post, kw)
                if mode[1] == 'billing':
                    order.partner_id = partner_id
                    order.with_context(not_self_saleperson=True).onchange_partner_id()
                    # This is the *only* thing that the front end user will see/edit anyway when choosing billing address
                    order.partner_invoice_id = partner_id

                elif mode[1] == 'shipping':
                    order.partner_shipping_id = partner_id

                order.message_partner_ids = [(4, partner_id), (3, request.website.partner_id.id)]

        return serialize_order(order)

    @http.route(['/shop/api/payment/transaction/'], type='json', auth="public", website=True)
    def api_payment_transaction(self, acquirer_id, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        if not acquirer_id:
            return False

        try:
            acquirer_id = int(acquirer_id)
        except:
            return False

        order = request.website.sale_get_order()

        # Ensure there is something to proceed
        if not order or (order and not order.order_line):
            return False

        assert order.partner_id.id != request.website.partner_id.id

        # Create transaction
        vals = {
            'acquirer_id': acquirer_id,
            'return_url': '/shop/payment/validate'
        }

        transaction = order._create_payment_transaction(vals)

        # store the new transaction into the transaction list and if there's an old one, we remove it
        # until the day the ecommerce supports multiple orders at the same time
        last_tx_id = request.session.get('__website_sale_last_tx_id')
        last_tx = request.env['payment.transaction'].browse(last_tx_id).sudo().exists()
        if last_tx:
            PaymentProcessing.remove_payment_transaction(last_tx)
        PaymentProcessing.add_payment_transaction(transaction)
        request.session['__website_sale_last_tx_id'] = transaction.id

        return transaction.render_sale_api_values(order)

    @http.route(['/shop/api/countries'], type='json', methods=['POST'], auth="public", website=True)
    def api_countries(self):
        country = request.env['res.country'].search([])
        return country.get_website_sale_countries().read(fields=['id', 'name', 'code'])

    @http.route(['/shop/api/states'], type='json', methods=['POST'], auth="public", website=True)
    def api_states(self, country_id):
        country = request.env['res.country'].browse(country_id)
        return country.get_website_sale_states().read(fields=['id', 'name', 'code'])

    @http.route(['/shop/api/acquirers'], type='json', methods=['POST'], auth="public", website=True)
    def api_acquirers(self, ):
        acquirers = request.env['payment.acquirer'].search([('state', '=', 'enabled')])
        return acquirers.read(fields=['id', 'name', 'provider', 'state'])
