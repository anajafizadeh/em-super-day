from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from constants import FX_FAILURE_COOLDOWN_SECONDS
from portfolio.fx_client import FxError
from portfolio.fx_service import apply_currency, get_exchange_rate
from utils import ApiError

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
NEXT_UPDATE = datetime(2026, 10, 4, 0, 0, 2, tzinfo=timezone.utc)


def _rate(rate='0.7020', as_of='2026-10-03T00:00:02.000Z', next_update=NEXT_UPDATE):
    return {'rate': Decimal(rate), 'as_of': as_of, 'next_update': next_update}


class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, **kwargs):
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock():
    clock = Clock(T0)
    with patch('portfolio.fx_service._now', clock):
        yield clock


@pytest.fixture
def fetch():
    with patch('portfolio.fx_service.fetch_pair_rate') as fetch:
        yield fetch


def test_native_currency_needs_no_fetch(fetch, clock):
    assert get_exchange_rate('CAD') == {'rate': Decimal(1), 'as_of': None}
    fetch.assert_not_called()


def test_rate_is_fetched_once_until_next_update(fetch, clock):
    fetch.return_value = _rate()

    first = get_exchange_rate('USD')
    clock.advance(hours=11)
    second = get_exchange_rate('USD')

    assert first == second == {'rate': Decimal('0.7020'), 'as_of': '2026-10-03T00:00:02.000Z'}
    fetch.assert_called_once_with('CAD', 'USD')


def test_rate_is_refetched_after_next_update(fetch, clock):
    fetch.side_effect = [_rate('0.7020'), _rate('0.7100', next_update=NEXT_UPDATE + timedelta(days=1))]
    get_exchange_rate('USD')
    clock.now = NEXT_UPDATE
    assert get_exchange_rate('USD')['rate'] == Decimal('0.7100')
    assert fetch.call_count == 2


def test_failure_with_cached_rate_serves_last_good_rate(fetch, clock):
    fetch.side_effect = [_rate(), FxError('timeout')]
    get_exchange_rate('USD')
    clock.now = NEXT_UPDATE + timedelta(minutes=1)

    stale = get_exchange_rate('USD')

    assert stale == {'rate': Decimal('0.7020'), 'as_of': '2026-10-03T00:00:02.000Z'}
    assert fetch.call_count == 2


def test_cold_failure_is_503(fetch, clock):
    fetch.side_effect = FxError('provider_invalid-key')
    with pytest.raises(ApiError) as exc_info:
        get_exchange_rate('USD')
    assert (exc_info.value.status, exc_info.value.error) == (503, 'fx_unavailable')


def test_cooldown_blocks_refetch_then_allows_it(fetch, clock):
    fetch.side_effect = [FxError('provider_quota-reached'), _rate()]

    with pytest.raises(ApiError):
        get_exchange_rate('USD')
    clock.advance(seconds=FX_FAILURE_COOLDOWN_SECONDS - 1)
    with pytest.raises(ApiError):
        get_exchange_rate('USD')
    assert fetch.call_count == 1

    clock.advance(seconds=1)
    assert get_exchange_rate('USD')['rate'] == Decimal('0.7020')
    assert fetch.call_count == 2


def test_success_after_failure_clears_cooldown(fetch, clock):
    fetch.side_effect = [_rate(), FxError('timeout'), _rate('0.7100', next_update=NEXT_UPDATE + timedelta(days=1))]
    get_exchange_rate('USD')
    clock.now = NEXT_UPDATE
    get_exchange_rate('USD')  # fails, serves stale
    clock.advance(seconds=FX_FAILURE_COOLDOWN_SECONDS)
    assert get_exchange_rate('USD')['rate'] == Decimal('0.7100')


def test_past_next_update_does_not_cause_a_fetch_per_request(fetch, clock):
    fetch.return_value = _rate(next_update=T0 - timedelta(hours=1))
    get_exchange_rate('USD')
    clock.advance(seconds=FX_FAILURE_COOLDOWN_SECONDS - 1)
    get_exchange_rate('USD')
    assert fetch.call_count == 1


def test_apply_currency_converts_object_and_adds_metadata(fetch, clock):
    fetch.return_value = _rate()
    result = apply_currency(
        {'currency': 'CAD', 'totalMarketValue': Decimal('48930'), 'dayChangePercent': Decimal('0.1')},
        ('totalMarketValue',), 'USD',
    )
    assert result == {
        'currency': 'USD',
        'totalMarketValue': Decimal('34348.86'),
        'dayChangePercent': Decimal('0.1'),
        'exchangeRate': Decimal('0.7020'),
        'exchangeRateAsOf': '2026-10-03T00:00:02.000Z',
    }


def test_apply_currency_native_keeps_values_unrounded(fetch, clock):
    record = {'currency': 'CAD', 'totalMarketValue': Decimal('48930.123')}
    result = apply_currency(record, ('totalMarketValue',), 'CAD')
    assert result['totalMarketValue'] == Decimal('48930.123')
    assert (result['exchangeRate'], result['exchangeRateAsOf']) == (Decimal(1), None)
    fetch.assert_not_called()


def test_apply_currency_handles_lists_and_empty_lists(fetch, clock):
    fetch.return_value = _rate()
    assert apply_currency([], ('marketValue',), 'USD') == []
    converted = apply_currency([{'marketValue': Decimal('100')}], ('marketValue',), 'USD')
    assert converted == [{
        'marketValue': Decimal('70.20'), 'currency': 'USD',
        'exchangeRate': Decimal('0.7020'), 'exchangeRateAsOf': '2026-10-03T00:00:02.000Z',
    }]
