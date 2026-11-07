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
