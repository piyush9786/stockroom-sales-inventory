"""Order lifecycle and stock mutations. Every public write is atomic."""
from datetime import date
from uuid import uuid4
from .db import query, execute, transaction
from .validation import (Problem, integer, text, iso_date,
                         order_totals, MAX_QUANTITY)


def require_admin(user):
    if user['role'] != 'Admin':
        raise Problem('Admin access is required.', 403)


def accessible_order(order_id, user, lock=False):
    order = query('SELECT * FROM sales_orders WHERE id=%s' + (' FOR UPDATE' if lock else ''),
                  (order_id,), one=True)
    if not order:
        raise Problem('Order not found.', 404)
    if user['role'] != 'Admin' and order['created_by'] != user['id']:
        raise Problem('You cannot access another user\'s order.', 403)
    return order


def order_detail(order_id, user):
    order = accessible_order(order_id, user)
    order['customer_name'] = query('SELECT name FROM customers WHERE id=%s',
                                   (order['customer_id'],), one=True)['name']
    order['items'] = query('''SELECT i.*, p.name AS product_name, p.product_code,
                             p.stock_quantity, p.status AS product_status
                             FROM sales_order_items i JOIN products p ON p.id=i.product_id
                             WHERE i.sales_order_id=%s ORDER BY i.id''', (order_id,))
    return order


def stock_movement(product_id, kind, change, user_id, reason, order_id=None):
    if change:
        execute('''INSERT INTO stock_movements
                   (product_id,movement_type,quantity_change,related_order_id,reason,created_by)
                   VALUES (%s,%s,%s,%s,%s,%s)''',
                (product_id, kind, change, order_id, reason, user_id))


def lock_products(product_ids):
    # A deterministic PK order prevents cross-product lock-order cycles.
    products = {}
    for product_id in sorted(product_ids):
        product = query('SELECT * FROM products WHERE id=%s FOR UPDATE',
                        (product_id,), one=True)
        if not product:
            raise Problem(f'Product {product_id} not found.', 404)
        products[product_id] = product
    return products


def save_order(data, user, order_id=None):
    customer_id = integer(data.get('customer_id'), 'Customer')
    order_date = iso_date(data.get('order_date', date.today().isoformat()))
    rows = data.get('items')
    if not isinstance(rows, list) or not rows:
        raise Problem('At least one order item is required.')
    if len(rows) > 100:
        raise Problem('An order may contain at most 100 products.')
    quantities = {}
    for row in rows:
        if not isinstance(row, dict):
            raise Problem('Each item must contain product_id and quantity.')
        pid = integer(row.get('product_id'), 'Product')
        if pid in quantities:
            raise Problem('Duplicate products are not allowed in one order.')
        quantities[pid] = integer(row.get('quantity'), 'Quantity')

    with transaction():
        old_rates = {}
        if order_id is not None:
            order = accessible_order(order_id, user, lock=True)
            if order['status'] != 'Draft':
                raise Problem('Only Draft orders can be edited.', 409)
            old_rates = {r['product_id']: r['rate'] for r in query(
                'SELECT product_id,rate FROM sales_order_items WHERE sales_order_id=%s', (order_id,))}
        customer = query('SELECT * FROM customers WHERE id=%s FOR SHARE',
                         (customer_id,), one=True)
        if not customer or customer['status'] != 'Active':
            raise Problem('Select an active customer.')
        products = lock_products(quantities)
        items = []
        for pid, quantity in quantities.items():
            product = products[pid]
            if product['status'] != 'Active':
                raise Problem(f'{product["name"]} is inactive.')
            # Retain the original rate for existing draft rows; price changes are not retroactive.
            rate = old_rates.get(pid, product['price'])
            items.append(dict(product_id=pid, quantity=quantity, rate=rate, amount=quantity * rate))
        totals = order_totals(items, data.get('discount_percentage', 0))
        if order_id is None:
            number = 'SO-' + uuid4().hex.upper()
            order_id = execute('''INSERT INTO sales_orders
                (order_number,customer_id,order_date,status,discount_percentage,subtotal,
                 discount_amount,grand_total,created_by)
                VALUES (%s,%s,%s,'Draft',%s,%s,%s,%s,%s)''',
                (number, customer_id, order_date, *totals, user['id']))
        else:
            execute('''UPDATE sales_orders SET customer_id=%s,order_date=%s,
                discount_percentage=%s,subtotal=%s,discount_amount=%s,grand_total=%s WHERE id=%s''',
                (customer_id, order_date, *totals, order_id))
            execute('DELETE FROM sales_order_items WHERE sales_order_id=%s', (order_id,))
        for row in items:
            execute('''INSERT INTO sales_order_items
                (sales_order_id,product_id,quantity,rate,amount) VALUES (%s,%s,%s,%s,%s)''',
                (order_id, row['product_id'], row['quantity'], row['rate'], row['amount']))
    return order_detail(order_id, user)


def transition_order(order_id, action, user):
    with transaction():
        order = accessible_order(order_id, user, lock=True)
        target = 'Confirmed' if action == 'confirm' else 'Cancelled'
        if order['status'] == target:
            return order_detail(order_id, user)  # safe retry: no second stock event
        if order['status'] == 'Cancelled':
            raise Problem('Cancelled orders cannot be changed.', 409)
        items = query('SELECT * FROM sales_order_items WHERE sales_order_id=%s', (order_id,))
        if action == 'confirm' or order['status'] == 'Confirmed':
            products = lock_products([row['product_id'] for row in items])
            # Validate every row before making even the first stock change.
            for row in items:
                product = products[row['product_id']]
                if action == 'confirm':
                    if product['status'] != 'Active':
                        raise Problem(f'{product["name"]} is inactive.', 409)
                    if product['stock_quantity'] < row['quantity']:
                        raise Problem(f'Insufficient stock for {product["name"]}: '
                                      f'{product["stock_quantity"]} available, {row["quantity"]} needed.', 409)
                elif product['stock_quantity'] + row['quantity'] > MAX_QUANTITY:
                    raise Problem('Restoration exceeds the supported stock limit.', 409)
            for row in items:
                change = -row['quantity'] if action == 'confirm' else row['quantity']
                execute('UPDATE products SET stock_quantity=stock_quantity+%s WHERE id=%s',
                        (change, row['product_id']))
                stock_movement(row['product_id'], 'Sale' if action == 'confirm' else 'Cancellation',
                               change, user['id'], f'Order {action}', order_id)
        execute('UPDATE sales_orders SET status=%s WHERE id=%s', (target, order_id))
    return order_detail(order_id, user)


def adjust_stock(product_id, data, user):
    require_admin(user)
    change = integer(data.get('quantity_change'), 'Quantity change', -MAX_QUANTITY)
    if change == 0:
        raise Problem('Quantity change must not be zero.')
    reason = text(data.get('reason'), 'Reason', 255)
    with transaction():
        product = lock_products([product_id])[product_id]
        new_stock = product['stock_quantity'] + change
        if not 0 <= new_stock <= MAX_QUANTITY:
            raise Problem('Adjustment would make stock negative or exceed the stock limit.', 409)
        execute('UPDATE products SET stock_quantity=%s WHERE id=%s', (new_stock, product_id))
        stock_movement(product_id, 'Adjustment', change, user['id'], reason)
    return query('SELECT * FROM products WHERE id=%s', (product_id,), one=True)


