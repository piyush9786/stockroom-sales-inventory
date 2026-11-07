import io
import pytest
from app.db import query

pytestmark = pytest.mark.integration
HEADER = 'product_code,product_name,category,price,stock_quantity,status\n'


def upload(clients, content, who='admin'):
    client, headers = clients[who]
    return client.post('/api/products/import',data={'file':(io.BytesIO(content.encode()),'products.csv')},headers=headers)


def test_invalid_row_rolls_back_entire_import(app, clients):
    response = upload(clients, HEADER+'NEW-1,Valid,Accessories,20,5,Active\nNEW-2,Invalid,Accessories,-1,5,Active\n')
    assert response.status_code == 400
    assert response.json['details'][0]['row'] == 3
    with app.app_context():
        assert query("SELECT id FROM products WHERE product_code LIKE 'NEW-%%'") == ()
        assert query("SELECT id FROM stock_movements WHERE reason='CSV opening stock'") == ()


def test_valid_import_records_opening_stock(app, clients):
    response = upload(clients, HEADER+'NEW-1,Keyboard,Accessories,1500,20,Active\nNEW-2,Mouse,Accessories,500,0,Inactive\n')
    assert response.status_code == 201 and response.json['imported'] == 2
    with app.app_context():
        rows = query("SELECT * FROM stock_movements WHERE reason='CSV opening stock'")
        assert len(rows) == 1 and rows[0]['quantity_change'] == 20


@pytest.mark.parametrize('content',[
    HEADER+'NEW-1,A,C,1,1,Active\nnew-1,B,C,1,1,Active\n',
    HEADER+'T-KEY,A,C,1,1,Active\n',
    HEADER+'NEW-1,A,C,NaN,1,Active\n',
    HEADER+'NEW-1,A,C,1,1.5,Active\n',
    HEADER+'NEW-1,A,C,1,-1,Active\n',
    HEADER+'NEW-1,A,C,1,1,Enabled\n',
    HEADER+'NEW-1,,C,1,1,Active\n',
    HEADER+'NEW-1,A,C,1,1,Active,unexpected\n',
    'product_code,name\nA,B\n', HEADER,
    HEADER+'NEW-1,"Unclosed,C,1,1,Active\n',
])
def test_bad_csv_rejected(app, clients, content):
    response = upload(clients, content)
    assert response.status_code == 400
    with app.app_context():
        assert query('SELECT COUNT(*) AS n FROM products',one=True)['n'] == 2


def test_sales_cannot_import(clients):
    assert upload(clients,HEADER+'NEW-1,A,C,1,1,Active\n','sales').status_code == 403


def test_concurrent_code_collision_rolls_back_with_row_number(app,data,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app import csv_import
    from app.validation import Problem
    barrier = Barrier(2)
    original = csv_import.query

    def synchronized_query(sql,params=(),**kwargs):
        result = original(sql,params,**kwargs)
        if 'WHERE product_code=' in sql:
            barrier.wait(timeout=10)  # both real validation reads finish before either insert
        return result

    monkeypatch.setattr(csv_import,'query',synchronized_query)
    raw = (HEADER+'RACE-1,Concurrent product,Cables,10,5,Active\n').encode()

    def attempt():
        with app.app_context():
            try:
                csv_import.import_products(raw,data['users']['admin'])
                return 201,None
            except Problem as error:
                return error.status,error.details

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert sorted(status for status,_ in results) == [201,409]
    assert next(details for status,details in results if status == 409)[0]['row'] == 2
    with app.app_context():
        assert query("SELECT COUNT(*) AS n FROM products WHERE product_code='RACE-1'",one=True)['n'] == 1
        assert query("SELECT COUNT(*) AS n FROM stock_movements WHERE reason='CSV opening stock'",one=True)['n'] == 1
