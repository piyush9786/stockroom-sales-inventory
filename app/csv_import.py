"""Admin-only product CSV validation and atomic import."""
import csv
import io
from .db import query, execute, transaction
from .validation import Problem, product_data
from .services import require_admin, stock_movement


CSV_COLUMNS = ['product_code', 'product_name', 'category', 'price', 'stock_quantity', 'status']


def import_products(raw, user):
    require_admin(user)
    try:
        content = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise Problem('CSV must use UTF-8 encoding.') from None
    reader = csv.DictReader(io.StringIO(content, newline=''), strict=True)
    errors, valid, seen = [], [], set()
    try:
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or set(reader.fieldnames) != set(CSV_COLUMNS):
            raise Problem('CSV headers must be exactly: ' + ','.join(CSV_COLUMNS))
        for row in reader:
            line = reader.line_num  # physical ending line; ordinary CSV records match spreadsheet row numbers
            try:
                if None in row or any(v is None for v in row.values()):
                    raise Problem('Row has the wrong number of columns.')
                record = product_data({**row, 'name': row['product_name']}, opening=True)
                code = record['product_code'].casefold()
                if code in seen:
                    raise Problem('Duplicate product code within file.')
                seen.add(code)
                valid.append((line, record))
            except Problem as error:
                errors.append({'row': line, 'reason': error.message})
            if len(valid) + len(errors) > 5000:
                raise Problem('Import is limited to 5000 rows.')
    except csv.Error as error:
        raise Problem('Malformed CSV.', details=[{'row': reader.line_num, 'reason': str(error)}]) from None
    if not valid and not errors:
        raise Problem('CSV must contain at least one product row.')
    with transaction():
        for line, record in valid:
            if query('SELECT id FROM products WHERE product_code=%s', (record['product_code'],), one=True):
                errors.append({'row': line, 'reason': 'Product code already exists in database.'})
        if errors:
            raise Problem('Import rejected. No products were imported.', details=sorted(errors, key=lambda e: e['row']))
        for _line, row in valid:
            pid = execute('''INSERT INTO products
                (product_code,name,category,price,stock_quantity,status) VALUES (%s,%s,%s,%s,%s,%s)''',
                tuple(row[k] for k in ('product_code','name','category','price','stock_quantity','status')))
            stock_movement(pid, 'Opening', row['stock_quantity'], user['id'], 'CSV opening stock')
    return {'imported': len(valid)}
