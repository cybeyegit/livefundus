import hashlib


def image_url(record, field, size=None):
    sudo_record = record.sudo()

    if not sudo_record[field]:
        return False

    sha = hashlib.sha1(str(getattr(sudo_record, '__last_update')).encode('utf-8')).hexdigest()[0:7]
    size = '' if size is None else '/%s' % size
    return '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, field, size, sha)


def serialize_order(order):
    order_json = order.read(
        fields=[
            'id',
            'name',
            'currency_id',
            'order_line',
            'amount_untaxed',
            'amount_tax',
            'amount_total',
            'amount_undiscounted',
            'cart_quantity',
            'partner_id',
            'partner_shipping_id'
        ]
    )

    for order_elem in order_json:
        order_elem['order_line'] = [serialize_order_line(order_line) for order_line in order.order_line]
        order_elem['partner_id'] = serialize_partner(order.partner_id)
        order_elem['partner_shipping_id'] = serialize_partner(order.partner_shipping_id)

    return order_json


def serialize_order_line(order_line):
    order_line_json = order_line.read(
        fields=['id', 'name', 'price_unit', 'price_subtotal', 'product_id', 'qty_to_deliver']
    )

    for order_line_elem in order_line_json:
        order_line_elem['product_id'] = serialize_products(order_line.product_id, max_depth=0)

    return order_line_json


def serialize_partner(partner):
    return partner.read(fields=[
        'id',
        'name',
        'email',
        'phone',
        'street',
        'street2',
        'zip',
        'city',
        'state_id',
        'country_id',
    ])


def serialize_products(products, max_depth=1, fields=None):
    if fields is None:
        fields = [
            'id',
            'name',
            'display_name',
            'description',
            'description_purchase',
            'description_sale',
            'price',
            'list_price',
            'volume',
            'volume_uom_name',
            'weight',
            'weight_uom_name',
            'sale_ok',
            'purchase_ok',
            'is_product_variant',
            'product_variant_count',
            'qty_available',
            'virtual_available',
            'incoming_qty',
            'outgoing_qty',
            'website_url'
        ]

    result = []

    for product in products:
        product_json = {
            'image_128': image_url(product, 'image_128'),
            'image_256': image_url(product, 'image_256'),
            'image_512': image_url(product, 'image_512'),
            'image_1024': image_url(product, 'image_1024')
        }

        for field in fields:
            if field.endswith('_id') or field.endswith('_ids'):
                product_json[field] = product[field].read()
            else:
                product_json[field] = product[field]

        if max_depth > 0:
            product_json['currency_id'] = product['currency_id'].read(
                fields=[
                    'id', 'display_name', 'symbol', 'decimal_places', 'currency_unit_label',
                    'currency_subunit_label'
                ]
            )
            product_json['product_variant_ids'] = serialize_products(product['product_variant_ids'],
                                                                     max_depth=max_depth - 1)

        result.append(product_json)

    return result


def serialize_categories(categories):
    result = []

    for categ in categories:
        categ_json = {
            'id': categ['id'],
            'name': categ['name'],
            'display_name': categ['display_name'],
            'image_128': image_url(categ, 'image_128'),
            'image_256': image_url(categ, 'image_256'),
            'image_512': image_url(categ, 'image_512'),
            'image_1024': image_url(categ, 'image_1024'),
            'child_id': serialize_categories(categ['child_id'])
        }

        result.append(categ_json)

    return result
