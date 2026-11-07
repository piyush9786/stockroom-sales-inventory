import pytest
from app.db import query, execute, transaction
from conftest import post

pytestmark = pytest.mark.integration


def test_pages_and_api_require_authentication(app,data):
    client = app.test_client()
    assert client.get('/orders').status_code == 302
    for path in ('/products','/customers','/orders','/reports/low-stock'):
        assert client.get('/api'+path).status_code == 401
    assert client.post('/api/orders',json={}).status_code == 401


def test_login_logout_csrf_and_secret_hiding(app,data):
    client = app.test_client()
    token = client.get('/api/session').json['csrf_token']
    assert client.post('/api/login',json={'email':'missing@example.test','password':'wrong'},headers={'X-CSRF-Token':token}).status_code == 401
    assert client.post('/api/login',json={}).status_code == 403
    from conftest import TEST_PASSWORD
    response = client.post('/api/login',json={'email':'admin@example.test','password':TEST_PASSWORD},headers={'X-CSRF-Token':token})
    assert response.status_code == 200
    assert 'password_hash' not in response.json['user']
    assert response.json['csrf_token'] != token
    headers = {'X-CSRF-Token':response.json['csrf_token']}
    assert client.post('/api/logout',headers=headers).status_code == 200
    assert client.get('/api/products').status_code == 401


def test_sales_cannot_modify_masters_adjust_stock_or_read_reports(clients,data):
    client, headers = clients['sales']
    pid = data['products'][0]
    for method,path in [('post','/products'),('put',f'/products/{pid}'),('delete',f'/products/{pid}'),('post','/customers'),('post',f'/products/{pid}/stock-adjustments')]:
        assert getattr(client,method)('/api'+path,json={},headers=headers).status_code == 403
    assert client.get('/reports').status_code == 403
    assert client.get('/api/reports/low-stock').status_code == 403


def test_active_only_search_filters_and_pagination(app,clients,data):
    with app.app_context(), transaction():
        execute("UPDATE products SET status='Inactive' WHERE id=%s",(data['products'][1],))
    sales = clients['sales'][0]
    assert sales.get('/api/products').json['total'] == 1
    assert sales.get(f'/api/products/{data["products"][1]}').status_code == 403
    assert sales.get('/api/products?status=All').status_code == 403
    admin = clients['admin'][0]
    result = admin.get('/api/products?status=All&per_page=1&page=2').json
    assert result['total'] == 2 and len(result['items']) == 1
    assert admin.get('/api/products?status=All&q=T-MOUSE&category=Accessories').json['total'] == 1
    assert admin.get('/api/products?per_page=0').status_code == 400
    for search in ('Acme','acme@example.test','9000000000'):
        assert admin.get('/api/customers',query_string={'q':search}).json['total'] == 1


def test_create_edit_customer_and_delete_only_unreferenced(clients,payload,data):
    admin, headers = clients['admin']
    values = dict(name='New Customer',email='new@example.test',mobile='9000000003',city='Pune',status='Active')
    result = admin.post('/api/customers',json=values,headers=headers)
    assert result.status_code == 201
    cid = result.json['id']
    assert admin.put(f'/api/customers/{cid}',json=dict(values,city='Mumbai'),headers=headers).json['city'] == 'Mumbai'
    assert admin.delete(f'/api/customers/{cid}',headers=headers).status_code == 204
    post(clients,'/orders',payload)
    assert admin.delete(f'/api/customers/{data["customer"]}',headers=headers).status_code == 409
    response = admin.put(f'/api/customers/{data["customer"]}',json=dict(values,status='Inactive'),headers=headers)
    assert response.status_code == 200
    assert post(clients,'/orders',payload).status_code == 400


def test_product_validation_and_safe_deletion(app,clients,data,payload):
    admin, headers = clients['admin']
    values = dict(product_code='NEW',name='New product',category='C',price='10.00',stock_quantity=0,status='Active')
    for changed in (dict(price=-1),dict(stock_quantity=-1),dict(stock_quantity=1.5),dict(product_code='T-KEY')):
        response = admin.post('/api/products',json={**values,**changed},headers=headers)
        assert response.status_code in (400,409)
    created = admin.post('/api/products',json=values,headers=headers)
    assert created.status_code == 201
    pid = created.json['id']
    assert admin.delete(f'/api/products/{pid}',headers=headers).status_code == 204
    # Opening movement alone prevents deletion.
    assert admin.delete(f'/api/products/{data["products"][0]}',headers=headers).status_code == 409
    # Even a zero-stock product is protected if a draft references it.
    created = admin.post('/api/products',json=dict(values,product_code='REF'),headers=headers)
    pid = created.json['id']
    payload['items'] = [dict(product_id=pid,quantity=1)]
    post(clients,'/orders',payload)
    assert admin.delete(f'/api/products/{pid}',headers=headers).status_code == 409
    assert admin.put(f'/api/products/{pid}',json=dict(values,product_code='REF',stock_quantity=5),headers=headers).status_code == 400


def test_stock_adjustment_reason_limits_and_movement(app,clients,data):
    pid = data['products'][0]
    for values, status in [({'quantity_change':1},400),({'quantity_change':0,'reason':'X'},400),({'quantity_change':-21,'reason':'X'},409)]:
        assert post(clients,f'/products/{pid}/stock-adjustments',values,'admin').status_code == status
    result = post(clients,f'/products/{pid}/stock-adjustments',{'quantity_change':-5,'reason':'Damaged goods'},'admin')
    assert result.json['stock_quantity'] == 15
    with app.app_context():
        record = query("SELECT * FROM stock_movements WHERE movement_type='Adjustment'",one=True)
        assert record['reason'] == 'Damaged goods' and record['quantity_change'] == -5


def test_missing_and_invalid_requests_are_clear_json(clients):
    client,headers = clients['admin']
    assert client.get('/api/orders/2147483647').status_code == 404
    assert client.get('/api/products/2147483647').status_code == 404
    assert client.post('/api/orders',data='broken',content_type='application/json',headers=headers).status_code == 400
    assert client.get('/api/reports/customer-sales?start_date=2026-12-01&end_date=2026-01-01').status_code == 400
