"""Authenticated JSON routes. Business calculations live in services/validation."""
import secrets
from datetime import date
from flask import Blueprint, g, jsonify, request, session
from werkzeug.security import check_password_hash
from .db import query, execute, transaction
from .services import (require_admin, order_detail, save_order, transition_order,
                       adjust_stock, stock_movement)
from .csv_import import import_products
from .validation import (Problem, integer, text, customer_data, product_data,
                         status_value, iso_date)

api = Blueprint('api', __name__, url_prefix='/api')


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise Problem('Send a JSON object with Content-Type application/json.')
    return data


def page_args():
    return (integer(request.args.get('page', 1), 'Page', maximum=1_000_000),
            integer(request.args.get('per_page', 20), 'Page size', maximum=100))


def listing(select, table, where, params, ordering='id DESC'):
    page, size = page_args()
    condition = ' WHERE ' + ' AND '.join(where) if where else ''
    total = query(f'SELECT COUNT(*) AS n FROM {table}{condition}', tuple(params), one=True)['n']
    rows = query(f'SELECT {select} FROM {table}{condition} ORDER BY {ordering} LIMIT %s OFFSET %s',
                 (*params, size, (page - 1) * size))
    return jsonify(items=rows, page=page, per_page=size, total=total)


@api.get('/session')
def session_info():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return jsonify(user=g.user, csrf_token=session['csrf_token'])


@api.post('/login')
def login():
    data = body()
    email = text(data.get('email'), 'Email', 254).lower()
    password = text(data.get('password'), 'Password', 1024)
    user = query('SELECT * FROM users WHERE email=%s', (email,), one=True)
    # A fixed dummy hash makes missing-account attempts do the same expensive verification work.
    stored = user['password_hash'] if user else DUMMY_HASH
    valid = check_password_hash(stored, password)
    if not user or not valid:
        raise Problem('Invalid email or password.', 401)
    session.clear()
    session.permanent = True
    session['user_id'] = user['id']
    session['csrf_token'] = secrets.token_urlsafe(32)
    return jsonify(user={key: user[key] for key in ('id', 'name', 'email', 'role')},
                   csrf_token=session['csrf_token'])


# This is a deliberately unusable account hash; there is no account or credential attached to it.
from werkzeug.security import generate_password_hash
DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))


@api.post('/logout')
def logout():
    session.clear()
    return jsonify(message='Logged out.')


@api.get('/<any(customers,products):kind>')
def masters(kind):
    where, params = [], []
    status = request.args.get('status', 'Active')
    if g.user['role'] != 'Admin' and status != 'Active':
        raise Problem('Sales Users may view active master data only.', 403)
    if status != 'All':
        where.append('status=%s')
        params.append(status_value(status))
    search = request.args.get('q', '').strip()
    if search:
        fields = ('name', 'email', 'mobile') if kind == 'customers' else ('product_code', 'name')
        where.append('(' + ' OR '.join(f'{field} LIKE %s' for field in fields) + ')')
        params.extend(['%' + search + '%'] * len(fields))
    if kind == 'products' and request.args.get('category'):
        where.append('category=%s')
        params.append(request.args['category'])
    return listing('*', kind, where, params)


@api.get('/<any(customers,products):kind>/<int:record_id>')
def master_detail(kind, record_id):
    record = query(f'SELECT * FROM {kind} WHERE id=%s', (record_id,), one=True)
    if not record:
        raise Problem('Record not found.', 404)
    if g.user['role'] != 'Admin' and record['status'] != 'Active':
        raise Problem('Sales Users may view active master data only.', 403)
    return jsonify(record)


@api.route('/<any(customers,products):kind>', methods=['POST'])
@api.route('/<any(customers,products):kind>/<int:record_id>', methods=['PUT'])
def save_master(kind, record_id=None):
    require_admin(g.user)
    data = body()
    if kind == 'products' and record_id and 'stock_quantity' in data:
        raise Problem('Use stock adjustment with a reason to change existing stock.')
    values = customer_data(data) if kind == 'customers' else product_data(data, opening=record_id is None)
    with transaction():
        if record_id is not None:
            if not query(f'SELECT id FROM {kind} WHERE id=%s FOR UPDATE', (record_id,), one=True):
                raise Problem('Record not found.', 404)
            fields = ','.join(f'{key}=%s' for key in values)
            execute(f'UPDATE {kind} SET {fields} WHERE id=%s', (*values.values(), record_id))
        else:
            fields = ','.join(values)
            marks = ','.join(['%s'] * len(values))
            record_id = execute(f'INSERT INTO {kind} ({fields}) VALUES ({marks})', tuple(values.values()))
            if kind == 'products':
                stock_movement(record_id, 'Opening', values['stock_quantity'], g.user['id'], 'Product opening stock')
    return jsonify(query(f'SELECT * FROM {kind} WHERE id=%s', (record_id,), one=True)), (201 if request.method == 'POST' else 200)


@api.delete('/<any(customers,products):kind>/<int:record_id>')
def delete_master(kind, record_id):
    require_admin(g.user)
    with transaction():
        if not query(f'SELECT id FROM {kind} WHERE id=%s FOR UPDATE', (record_id,), one=True):
            raise Problem('Record not found.', 404)
        # ON DELETE RESTRICT also protects concurrent inserts referencing this record.
        execute(f'DELETE FROM {kind} WHERE id=%s', (record_id,))
    return '', 204


@api.post('/products/<int:product_id>/stock-adjustments')
def stock_adjustment(product_id):
    return jsonify(adjust_stock(product_id, body(), g.user))


@api.post('/products/import')
def product_import():
    require_admin(g.user)
    uploaded = request.files.get('file')
    if uploaded is None:
        raise Problem('Upload a CSV using multipart field "file".')
    return jsonify(import_products(uploaded.read(), g.user)), 201


@api.get('/orders')
def orders():
    where, params = [], []
    if g.user['role'] != 'Admin':
        where.append('o.created_by=%s')
        params.append(g.user['id'])
    if request.args.get('status'):
        if request.args['status'] not in ('Draft', 'Confirmed', 'Cancelled'):
            raise Problem('Invalid order status.')
        where.append('o.status=%s')
        params.append(request.args['status'])
    if request.args.get('q'):
        where.append('(o.order_number LIKE %s OR c.name LIKE %s)')
        params.extend(['%' + request.args['q'] + '%'] * 2)
    return listing('o.*, c.name AS customer_name, u.name AS owner_name',
                   'sales_orders o JOIN customers c ON c.id=o.customer_id JOIN users u ON u.id=o.created_by',
                   where, params, 'o.id DESC')


@api.post('/orders')
def create_order():
    return jsonify(save_order(body(), g.user)), 201


@api.get('/orders/<int:order_id>')
def get_order(order_id):
    return jsonify(order_detail(order_id, g.user))


@api.put('/orders/<int:order_id>')
def edit_order(order_id):
    return jsonify(save_order(body(), g.user, order_id))


@api.post('/orders/<int:order_id>/<any(confirm,cancel):action>')
def order_action(order_id, action):
    return jsonify(transition_order(order_id, action, g.user))


def report_dates():
    start = iso_date(request.args.get('start_date', '1000-01-01'), 'Start date')
    end = iso_date(request.args.get('end_date', '9999-12-31'), 'End date')
    if start > end:
        raise Problem('Start date must be on or before end date.')
    return start, end


@api.get('/reports/<any(customer-sales,product-sales,low-stock,stock-movements):kind>')
def reports(kind):
    require_admin(g.user)
    if kind == 'customer-sales':
        start, end = report_dates()
        # Filter in JOIN, not WHERE: customers without matching confirmed orders remain.
        rows = query('''SELECT c.id,c.name AS customer,COUNT(o.id) AS confirmed_order_count,
                        COALESCE(SUM(o.grand_total),0) AS total_sales
                        FROM customers c LEFT JOIN sales_orders o ON o.customer_id=c.id
                        AND o.status='Confirmed' AND o.order_date BETWEEN %s AND %s
                        GROUP BY c.id,c.name ORDER BY total_sales DESC,c.id''', (start, end))
    elif kind == 'product-sales':
        start, end = report_dates()
        rows = query('''SELECT p.id,p.product_code,p.name AS product,
                        SUM(i.quantity) AS quantity_sold,SUM(i.amount) AS gross_item_value
                        FROM products p JOIN sales_order_items i ON i.product_id=p.id
                        JOIN sales_orders o ON o.id=i.sales_order_id
                        WHERE o.status='Confirmed' AND o.order_date BETWEEN %s AND %s
                        GROUP BY p.id,p.product_code,p.name ORDER BY quantity_sold DESC,p.id''', (start, end))
    elif kind == 'low-stock':
        threshold = integer(request.args.get('threshold', 10), 'Threshold', 0)
        rows = query('SELECT id,product_code,name AS product,category,stock_quantity,status FROM products '
                     'WHERE stock_quantity < %s ORDER BY stock_quantity,id', (threshold,))
    else:
        where, params = [], []
        if request.args.get('product_id'):
            where.append('m.product_id=%s')
            params.append(integer(request.args['product_id'], 'Product'))
        return listing('m.id,p.name AS product,p.product_code,m.movement_type,m.quantity_change,'
                       'o.order_number,m.reason,m.created_at,u.name AS created_by',
                       'stock_movements m JOIN products p ON p.id=m.product_id '
                       'LEFT JOIN sales_orders o ON o.id=m.related_order_id JOIN users u ON u.id=m.created_by',
                       where, params, 'm.id DESC')
    return jsonify(items=rows)
