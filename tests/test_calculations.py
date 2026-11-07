from decimal import Decimal
import pytest
from app.validation import Problem, calculate_total, order_totals, integer, decimal_value


def test_debugging_example_sums_instead_of_overwriting():
    assert calculate_total([{'qty':2,'rate':100},{'qty':3,'rate':50}]) == Decimal('350.00')


def test_empty_list_returns_decimal_zero():
    assert calculate_total([]) == Decimal('0.00')


@pytest.mark.parametrize('item',[
    {'qty':1}, {'rate':10}, {}, None,
    {'qty':0,'rate':10}, {'qty':-1,'rate':10}, {'qty':1.5,'rate':10},
    {'qty':True,'rate':10}, {'qty':1,'rate':-1}, {'qty':1,'rate':'NaN'},
    {'qty':1,'rate':'Infinity'}, {'qty':1,'rate':'1.001'}, {'qty':'bad','rate':10},
])
def test_debugging_invalid_input_is_explicit(item):
    with pytest.raises(Problem):
        calculate_total([item])


def test_exact_decimal_math_and_half_up_discount():
    values = order_totals([{'quantity':1,'rate':Decimal('0.05')}],10)
    assert values == (Decimal('10.00'),Decimal('0.05'),Decimal('0.01'),Decimal('0.04'))
    assert calculate_total([{'qty':3,'rate':'0.10'}]) == Decimal('0.30')


@pytest.mark.parametrize('discount',[-1,'20.01',21,'NaN',True])
def test_invalid_discounts(discount):
    with pytest.raises(Problem):
        order_totals([{'quantity':1,'rate':Decimal('1')}],discount)
