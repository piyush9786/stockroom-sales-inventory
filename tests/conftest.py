"""Real-MySQL integration fixtures. Never point TEST_DB_NAME at a working database."""
import os
import pytest
from werkzeug.security import generate_password_hash
from app import ROOT, create_app, load_environment, run_sql_file
from app.db import query, execute, transaction

TEST_PASSWORD = 'Only-for-automated-tests!'


@pytest.fixture(scope='session')
def app():
    load_environment()
    name = os.environ.get('TEST_DB_NAME', 'sales_inventory_test')
    if not name.endswith('_test') or name == os.environ.get('DB_NAME', 'sales_inventory'):
        pytest.fail('TEST_DB_NAME must end in _test and differ from DB_NAME.')
    application = create_app({'TESTING':True, 'DB_NAME':name,
                              'SECRET_KEY':'test-only-secret-value-at-least-32-characters'})
    with application.app_context():
        # Destructive only in the explicitly separate test database.
        for table in ('stock_movements','sales_order_items','sales_orders','products','customers','users'):
            execute(f'DROP TABLE IF EXISTS {table}')
        run_sql_file(ROOT / 'sql' / 'schema.sql')
    return application


@pytest.fixture(scope='session')
def password_hash():
    return generate_password_hash(TEST_PASSWORD)


@pytest.fixture
def data(app, password_hash):
    with app.app_context(), transaction():
        for table in ('stock_movements','sales_order_items','sales_orders','products','customers','users'):
            execute(f'DELETE FROM {table}')
        users = {}
        for name, role in [('admin','Admin'),('sales','Sales User'),('other','Sales User')]:
            uid = execute('INSERT INTO users (name,email,password_hash,role) VALUES (%s,%s,%s,%s)',
                          (name, name+'@example.test',password_hash,role))
            users[name] = dict(id=uid,name=name,email=name+'@example.test',role=role)
        cid = execute("INSERT INTO customers (name,email,mobile,city,status) VALUES ('Acme','acme@example.test','9000000000','Pune','Active')")
        empty_cid = execute("INSERT INTO customers (name,email,mobile,city,status) VALUES ('No sales','empty@example.test','9000000001','Mumbai','Active')")
        pids = []
        for code, name, price, stock in [('T-KEY','Keyboard',1500,20),('T-MOUSE','Mouse',500,50)]:
            pid = execute("INSERT INTO products (product_code,name,category,price,stock_quantity,status) VALUES (%s,%s,'Accessories',%s,%s,'Active')",(code,name,price,stock))
            execute("INSERT INTO stock_movements (product_id,movement_type,quantity_change,reason,created_by) VALUES (%s,'Opening',%s,'Test fixture',%s)", (pid,stock,users['admin']['id']))
            pids.append(pid)
    return dict(users=users,customer=cid,empty_customer=empty_cid,products=pids)


@pytest.fixture
def clients(app, data):
    results = {}
    for name, user in data['users'].items():
        client = app.test_client()
        token = client.get('/api/session').json['csrf_token']
        response = client.post('/api/login',json=dict(email=user['email'],password=TEST_PASSWORD),
                               headers={'X-CSRF-Token':token})
        assert response.status_code == 200
        results[name] = (client,{'X-CSRF-Token':response.json['csrf_token']})
    return results


@pytest.fixture
def payload(data):
    return dict(customer_id=data['customer'],order_date='2026-11-07',discount_percentage='10',
                items=[dict(product_id=data['products'][0],quantity=2),
                       dict(product_id=data['products'][1],quantity=3)])


def post(clients, path, payload=None, who='sales'):
    client, headers = clients[who]
    return client.post('/api'+path,json=payload,headers=headers)
