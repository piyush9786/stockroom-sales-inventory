from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from app.db import query, execute, transaction
from app.services import save_order, transition_order
from app.validation import Problem
from conftest import post

pytestmark = pytest.mark.integration


def stock(app, data):
    with app.app_context():
        return [query('SELECT stock_quantity AS n FROM products WHERE id=%s',(pid,),one=True)['n'] for pid in data['products']]


def test_multiple_items_discount_and_untrusted_browser_fields(app, clients, payload, data):
    payload.update(status='Confirmed',created_by=data['users']['admin']['id'],grand_total=1,subtotal=1)
    payload['items'][0]['rate'] = '0.01'
    response = post(clients,'/orders',payload)
    assert response.status_code == 201
    order = response.json
    assert (order['subtotal'],order['discount_amount'],order['grand_total']) == ('4500.00','450.00','4050.00')
    assert order['status'] == 'Draft' and order['created_by'] == data['users']['sales']['id']
    assert order['items'][0]['rate'] == '1500.00'
    assert stock(app,data) == [20,50]


@pytest.mark.parametrize('quantity',[0,-1,1.5,True,'abc'])
def test_invalid_quantity_rejected(clients,payload,quantity):
    payload['items'][0]['quantity'] = quantity
    assert post(clients,'/orders',payload).status_code == 400


@pytest.mark.parametrize('discount',[-1,21,'20.01','NaN'])
def test_out_of_range_discount_rejected(clients,payload,discount):
    payload['discount_percentage'] = discount
    assert post(clients,'/orders',payload).status_code == 400


def test_empty_and_duplicate_items_rejected(clients,payload):
    original = payload['items'][0]
    payload['items'] = []
    assert post(clients,'/orders',payload).status_code == 400
    payload['items'] = [original,original]
    assert post(clients,'/orders',payload).status_code == 400


def test_confirmation_and_retry_deduct_only_once(app,clients,payload,data):
    oid = post(clients,'/orders',payload).json['id']
    assert post(clients,f'/orders/{oid}/confirm').json['status'] == 'Confirmed'
    assert post(clients,f'/orders/{oid}/confirm').status_code == 200
    assert stock(app,data) == [18,47]
    with app.app_context():
        assert query("SELECT COUNT(*) AS n FROM stock_movements WHERE movement_type='Sale'",one=True)['n'] == 2


def test_insufficient_item_leaves_everything_unchanged(app,clients,payload,data):
    payload['items'][1]['quantity'] = 51
    oid = post(clients,'/orders',payload).json['id']
    assert post(clients,f'/orders/{oid}/confirm').status_code == 409
    assert stock(app,data) == [20,50]
    with app.app_context():
        assert query('SELECT status FROM sales_orders WHERE id=%s',(oid,),one=True)['status'] == 'Draft'
        assert query("SELECT COUNT(*) AS n FROM stock_movements WHERE movement_type='Sale'",one=True)['n'] == 0


def test_confirmed_cancellation_restores_once_and_readonly(app,clients,payload,data):
    oid = post(clients,'/orders',payload).json['id']
    post(clients,f'/orders/{oid}/confirm')
    client, headers = clients['sales']
    assert client.put(f'/api/orders/{oid}',json=payload,headers=headers).status_code == 409
    assert post(clients,f'/orders/{oid}/cancel').json['status'] == 'Cancelled'
    assert post(clients,f'/orders/{oid}/cancel').status_code == 200
    assert post(clients,f'/orders/{oid}/confirm').status_code == 409
    assert client.put(f'/api/orders/{oid}',json=payload,headers=headers).status_code == 409
    assert stock(app,data) == [20,50]
    with app.app_context():
        assert query("SELECT COUNT(*) AS n FROM stock_movements WHERE movement_type='Cancellation'",one=True)['n'] == 2


def test_draft_cancel_never_changes_stock(app,clients,payload,data):
    oid = post(clients,'/orders',payload).json['id']
    assert post(clients,f'/orders/{oid}/cancel').json['status'] == 'Cancelled'
    assert stock(app,data) == [20,50]


def test_draft_edit_rows_and_rate_snapshot(app,clients,payload,data):
    order = post(clients,'/orders',payload).json
    with app.app_context(), transaction():
        execute('UPDATE products SET price=9999 WHERE id=%s',(data['products'][0],))
    payload['items'] = [dict(product_id=data['products'][0],quantity=3)]
    client,headers = clients['sales']
    edited = client.put(f'/api/orders/{order["id"]}',json=payload,headers=headers).json
    assert len(edited['items']) == 1
    assert edited['items'][0]['rate'] == '1500.00'
    assert edited['subtotal'] == '4500.00'
    payload['items'].append(dict(product_id=data['products'][1],quantity=1))
    assert len(client.put(f'/api/orders/{order["id"]}',json=payload,headers=headers).json['items']) == 2
    assert stock(app,data) == [20,50]


def test_sales_user_cannot_access_other_orders(clients,payload):
    oid = post(clients,'/orders',payload).json['id']
    client,headers = clients['other']
    assert client.get(f'/api/orders/{oid}').status_code == 403
    assert client.put(f'/api/orders/{oid}',json=payload,headers=headers).status_code == 403
    for action in ('confirm','cancel'):
        assert client.post(f'/api/orders/{oid}/{action}',headers=headers).status_code == 403
    assert client.get('/api/orders').json['total'] == 0
    assert clients['admin'][0].get(f'/api/orders/{oid}').status_code == 200


def test_two_simultaneous_confirmations_cannot_oversell(app,data,payload):
    payload['items'] = [dict(product_id=data['products'][0],quantity=15)]
    with app.app_context():
        first = save_order(payload,data['users']['sales'])['id']
        second = save_order(payload,data['users']['other'])['id']
    barrier = Barrier(2)
    def confirm(oid,who):
        with app.app_context():
            barrier.wait(timeout=10)
            try:
                transition_order(oid,'confirm',data['users'][who]); return 200
            except Problem as error:
                return error.status
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(confirm,first,'sales'),executor.submit(confirm,second,'other')]
        assert sorted(f.result(timeout=20) for f in futures) == [200,409]
    assert stock(app,data) == [5,50]
    with app.app_context():
        assert query("SELECT COUNT(*) AS n FROM sales_orders WHERE status='Confirmed'",one=True)['n'] == 1


def test_simultaneous_retries_of_same_order_only_change_once(app,data,payload):
    with app.app_context():
        oid = save_order(payload,data['users']['sales'])['id']
    for action, expected in [('confirm',[18,47]),('cancel',[20,50])]:
        barrier = Barrier(2)
        def change():
            with app.app_context():
                barrier.wait(timeout=10)
                return transition_order(oid,action,data['users']['sales'])['status']
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(change) for _ in range(2)]
            for future in futures:
                assert future.result(timeout=20) == ('Confirmed' if action == 'confirm' else 'Cancelled')
        assert stock(app,data) == expected
