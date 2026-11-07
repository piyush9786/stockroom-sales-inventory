"""Bills are protected read-only views of confirmed orders, not new stock events."""
import pytest
from app.db import query, execute, transaction
from conftest import post

pytestmark = pytest.mark.integration


def test_landing_is_public_and_workspace_stays_protected(app,data):
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b'Less juggling.' in response.data and b'Enter your workspace' in response.data
    assert client.get('/orders').status_code == 302
    assert client.get('/orders/1/bill').headers['Location'] == '/login'


@pytest.mark.parametrize('layout',['receipt','invoice'])
def test_confirmed_bill_uses_saved_values_and_does_not_change_stock(app,clients,payload,data,layout):
    order = post(clients,'/orders',payload).json
    oid = order['id']
    post(clients,f'/orders/{oid}/confirm')
    with app.app_context(), transaction():
        execute('UPDATE products SET price=9999 WHERE id=%s',(data['products'][0],))
    with app.app_context():
        before = query('SELECT id,stock_quantity FROM products ORDER BY id')
        movements = query('SELECT COUNT(*) AS n FROM stock_movements',one=True)['n']
    client = clients['sales'][0]
    response = client.get(f'/orders/{oid}/bill?format={layout}&grand_total=1&rate=0')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for expected in ('4,500.00','450.00','4,050.00','1,500.00','Keyboard','Mouse',order['order_number'],f'BILL-{oid:06d}','Print / Save PDF'):
        assert expected in html
    assert layout+'-layout' in html
    assert '9,999.00' not in html
    assert clients['admin'][0].get(f'/orders/{oid}/bill').status_code == 200
    with app.app_context():
        assert query('SELECT id,stock_quantity FROM products ORDER BY id') == before
        assert query('SELECT COUNT(*) AS n FROM stock_movements',one=True)['n'] == movements


def test_bill_requires_confirmed_state_and_owner(clients,payload):
    oid = post(clients,'/orders',payload).json['id']
    sales, _headers = clients['sales']
    assert sales.get(f'/orders/{oid}/bill').status_code == 409
    post(clients,f'/orders/{oid}/confirm')
    assert clients['other'][0].get(f'/orders/{oid}/bill').status_code == 403
    assert sales.get(f'/orders/{oid}/bill?format=unknown').status_code == 400
    post(clients,f'/orders/{oid}/cancel')
    assert sales.get(f'/orders/{oid}/bill').status_code == 409
    assert sales.get('/orders/2147483647/bill').status_code == 404


def test_shop_and_customer_details_are_escaped(app,clients,payload,data):
    oid = post(clients,'/orders',payload).json['id']
    post(clients,f'/orders/{oid}/confirm')
    with app.app_context(), transaction():
        execute('UPDATE customers SET name=%s WHERE id=%s',('<script>alert(1)</script>',data['customer']))
    old = app.config['SHOP_NAME']
    app.config['SHOP_NAME'] = '<img src=x onerror=alert(1)>'
    try:
        html = clients['sales'][0].get(f'/orders/{oid}/bill').get_data(as_text=True)
        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
        assert '<img src=x onerror=alert(1)>' not in html
        assert '&lt;img src=x onerror=alert(1)&gt;' in html
    finally:
        app.config['SHOP_NAME'] = old
