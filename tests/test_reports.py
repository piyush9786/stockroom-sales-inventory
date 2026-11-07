import pytest
from conftest import post

pytestmark = pytest.mark.integration


def test_customer_summary_zeros_range_and_no_item_multiplication(clients,payload,data):
    oid = post(clients,'/orders',payload).json['id']
    post(clients,f'/orders/{oid}/confirm')
    # Another Draft and a Cancelled order must be absent from sales totals.
    post(clients,'/orders',payload)
    cancelled = post(clients,'/orders',payload).json['id']
    post(clients,f'/orders/{cancelled}/confirm')
    post(clients,f'/orders/{cancelled}/cancel')
    admin = clients['admin'][0]
    rows = admin.get('/api/reports/customer-sales?start_date=2026-11-01&end_date=2026-11-30').json['items']
    by_id = {row['id']:row for row in rows}
    assert by_id[data['customer']]['confirmed_order_count'] == 1
    assert by_id[data['customer']]['total_sales'] == '4050.00'
    assert by_id[data['empty_customer']]['confirmed_order_count'] == 0
    assert by_id[data['empty_customer']]['total_sales'] == '0.00'
    outside = admin.get('/api/reports/customer-sales?start_date=2027-01-01&end_date=2027-12-31').json['items']
    assert len(outside) == 2 and all(row['confirmed_order_count'] == 0 and row['total_sales'] == '0.00' for row in outside)


def test_product_gross_sales_low_stock_and_history(clients,payload,data):
    oid = post(clients,'/orders',payload).json['id']
    post(clients,f'/orders/{oid}/confirm')
    admin = clients['admin'][0]
    rows = admin.get('/api/reports/product-sales').json['items']
    by_id = {row['id']:row for row in rows}
    assert by_id[data['products'][0]]['quantity_sold'] == 2
    assert by_id[data['products'][0]]['gross_item_value'] == '3000.00'
    assert by_id[data['products'][1]]['gross_item_value'] == '1500.00'
    assert len(admin.get('/api/reports/low-stock?threshold=19').json['items']) == 1
    assert admin.get('/api/reports/low-stock?threshold=18').json['items'] == []
    history = admin.get('/api/reports/stock-movements',query_string={'product_id':data['products'][0]}).json
    assert history['total'] == 2
    assert history['items'][0]['quantity_change'] == -2
    assert history['items'][0]['order_number'] is not None
