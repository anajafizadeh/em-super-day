from decimal import Decimal

import pytest

from portfolio.currency import (
    HOLDING_MONEY_FIELDS, convert_amount, convert_record, normalize_currency,
)
from utils import ApiError


@pytest.mark.parametrize('raw, expected', [
    (None, 'CAD'),
    ('', 'CAD'),
    ('   ', 'CAD'),
    ('CAD', 'CAD'),
    (' usd ', 'USD'),
    ('Usd', 'USD'),
])
def test_currency_is_normalized(raw, expected):
    assert normalize_currency(raw) == expected


@pytest.mark.parametrize('raw', ['EUR', 'US D', 'usdx', 'cad,usd'])
def test_unsupported_currency_is_400(raw):
    with pytest.raises(ApiError) as exc_info:
        normalize_currency(raw)
    assert (exc_info.value.status, exc_info.value.error) == (400, 'unsupported_currency')


@pytest.mark.parametrize('amount, rate, expected', [
    (Decimal('48930'), Decimal('0.7020'), Decimal('34348.86')),
    (Decimal('0.005'), Decimal('1'), Decimal('0.01')),      # HALF_UP, not banker's
    (Decimal('-0.005'), Decimal('1'), Decimal('-0.01')),
    (Decimal('227.5'), Decimal('0.7020'), Decimal('159.71')),  # 159.705 rounds up
    (Decimal('0'), Decimal('0.7020'), Decimal('0.00')),
])
def test_convert_amount_rounds_half_up_to_cents(amount, rate, expected):
    assert convert_amount(amount, rate) == expected


def test_convert_amount_keeps_none():
    assert convert_amount(None, Decimal('0.7')) is None


def test_convert_record_touches_only_money_fields():
    holding = {
        'ticker': 'AAPL', 'quantity': Decimal('120'), 'price': Decimal('227.5'),
        'costBasisPerShare': Decimal('200'), 'previousClosePrice': Decimal('225'),
        'marketValue': Decimal('27300'), 'weightPercent': Decimal('0.5579'),
        'unrealizedGainLoss': Decimal('3300'), 'dayChangeAmount': Decimal('300'),
        'dayChangePercent': Decimal('0.0111'),
    }
    converted = convert_record(holding, HOLDING_MONEY_FIELDS, Decimal('0.7020'))

    assert converted['marketValue'] == Decimal('19164.60')
    assert converted['price'] == Decimal('159.71')
    for untouched in ('ticker', 'quantity', 'weightPercent', 'dayChangePercent'):
        assert converted[untouched] == holding[untouched]
    assert holding['marketValue'] == Decimal('27300')  # source not mutated


def test_convert_record_ignores_absent_fields():
    assert convert_record({'a': 1}, ('marketValue',), Decimal('2')) == {'a': 1}
