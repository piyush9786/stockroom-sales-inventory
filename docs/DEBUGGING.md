# Debugging exercise

The supplied loop assigns `total = amount` on every iteration. That **overwrites** the
previous amount, so the example returns only the last item's 150 instead of 350.
The correction accumulates each amount. The production function is
`calculate_total` in `app/validation.py`; order calculations use this same implementation.

```python
def calculate_total(items):
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
```

- The example `[{"qty":2,"rate":100},{"qty":3,"rate":50}]` returns Decimal `350.00`.
- Empty list returns Decimal `0.00`.
- Missing `qty` or `rate`, or a non-dictionary row, raises a clear `Problem` validation
  error. Required values are never silently treated as zero.
- Quantity must be a positive whole number; zero, negative, boolean and fractional
  quantities are rejected. A rate must be finite, numeric, nonnegative and have at most
  two fractional decimals. Zero price is valid. NaN, infinity and excessive amounts fail.
- Decimal arithmetic avoids binary floating-point accumulation errors. Money rounds
  consistently with `ROUND_HALF_UP` to two decimal places.

`tests/test_calculations.py` verifies the given example, empty input, missing fields,
invalid quantity/rate cases, exact 0.10 arithmetic and half-cent discount rounding:

```bash
python -m pytest tests/test_calculations.py -q
```
