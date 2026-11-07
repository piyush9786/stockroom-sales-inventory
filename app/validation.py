"""Shared strict validation and Decimal/ROUND_HALF_UP monetary arithmetic."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal('0.01')
MAX_MONEY = Decimal('999999999999.99')
MAX_QUANTITY = 2_000_000_000


class Problem(Exception):
    def __init__(self, message, status=400, details=None):
        super().__init__(message)
        self.message, self.status, self.details = message, status, details


def text(value, field, maximum=120):
    if not isinstance(value, str) or not value.strip():
        raise Problem(f'{field} is required.')
    value = value.strip()
    if len(value) > maximum:
        raise Problem(f'{field} must be at most {maximum} characters.')
    return value


def integer(value, field, minimum=1, maximum=MAX_QUANTITY):
    if isinstance(value, bool) or not re.fullmatch(r'-?\d+', str(value)):
        raise Problem(f'{field} must be a whole number.')
    result = int(value)
    if not minimum <= result <= maximum:
        raise Problem(f'{field} must be between {minimum} and {maximum}.')
    return result


def decimal_value(value, field, minimum=Decimal('0'), maximum=MAX_MONEY):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise Problem(f'{field} must be a valid number.') from None
    if not result.is_finite() or not minimum <= result <= maximum:
        raise Problem(f'{field} must be between {minimum} and {maximum}.')
    if result != result.quantize(CENT, rounding=ROUND_HALF_UP):
        raise Problem(f'{field} must have at most two decimal places.')
    return result.quantize(CENT, rounding=ROUND_HALF_UP)


def money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def status_value(value):
    if value not in ('Active', 'Inactive'):
        raise Problem('Status must be Active or Inactive.')
    return value


def iso_date(value, field='Order date'):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise Problem(f'{field} must use YYYY-MM-DD.')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Problem(f'{field} is invalid.') from None


def customer_data(data):
    result = {key: text(data.get(key), key.title(), limit) for key, limit in
              [('name', 120), ('email', 254), ('mobile', 30), ('city', 120)]}
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', result['email']):
        raise Problem('Email is invalid.')
    if not re.fullmatch(r'\+?[0-9 ()-]{7,30}', result['mobile']):
        raise Problem('Mobile is invalid.')
    result['status'] = status_value(data.get('status', 'Active'))
    return result


def product_data(data, opening=False):
    result = {key: text(data.get(key), key.replace('_', ' ').title(), limit)
              for key, limit in [('product_code', 50), ('name', 160), ('category', 100)]}
    if not re.fullmatch(r'[A-Za-z0-9_-]+', result['product_code']):
        raise Problem('Product code may contain letters, numbers, underscores and hyphens.')
    result['price'] = decimal_value(data.get('price'), 'Price')
    result['status'] = status_value(data.get('status', 'Active'))
    if opening:
        result['stock_quantity'] = integer(data.get('stock_quantity', 0), 'Stock quantity', 0)
    return result


def calculate_total(items):
    """Debugging exercise: sum validated qty/rate rows; empty list is 0.00."""
    total = Decimal('0.00')
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict) or 'qty' not in item or 'rate' not in item:
            raise Problem(f'Item {index} requires qty and rate.')
        quantity = integer(item['qty'], f'Item {index} quantity')
        rate = decimal_value(item['rate'], f'Item {index} rate')
        total += money(quantity * rate)
        if total > MAX_MONEY:
            raise Problem('Total exceeds the supported monetary limit.')
    return money(total)


def order_totals(items, discount):
    percentage = decimal_value(discount, 'Discount percentage', maximum=Decimal('20'))
    subtotal = calculate_total([{'qty': row['quantity'], 'rate': row['rate']} for row in items])
    discount_amount = money(subtotal * percentage / Decimal('100'))
    return percentage, subtotal, discount_amount, money(subtotal - discount_amount)
