"""HTTP tests for ?currency on /portfolios/:id and /portfolios/:id/holdings (Task 7)."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from portfolio.fx_client import FxError
from portfolio.holdings import calculate_holdings

PORTFOLIO = {
    'portfolioId': 'P-9001',
    'clientId': 'abc123',
    'label': 'Taxable Brokerage',
    'currency': 'CAD',
    'totalMarketValue': Decimal('48930'),
    'dayChangeAmount': Decimal('30'),
    'dayChangePercent': Decimal('0.0006134969325153374'),
    'totalReturnSinceInception': Decimal('0.187'),
    'asOf': '2026-10-03T16:52:06.123Z',
}
HOLDINGS_SOURCE = [
    {'ticker': 'AAPL', 'name': 'Apple Inc.', 'assetClass': 'Equity', 'quantity': 120,
     'costBasisPerShare': 200, 'price': Decimal('227.5'), 'previousClosePrice': 225},
    {'ticker': 'BND', 'name': 'Vanguard Total Bond Market ETF', 'assetClass': 'Fixed Income',
     'quantity': 300, 'costBasisPerShare': Decimal('74'), 'price': Decimal('72.1'),
     'previousClosePrice': Decimal('73')},
]
RATE = {
    'rate': Decimal('0.7020'),
    'as_of': '2026-10-03T00:00:02.000Z',
    'next_update': datetime(2099, 1, 1, tzinfo=timezone.utc),
}


@pytest.fixture
def crm():
    with patch('portfolio.services.get_crm_data', return_value=dict(PORTFOLIO)) as get_crm_data:
        yield get_crm_data


@pytest.fixture
def holdings():
    with patch('portfolio.services.get_holdings',
               side_effect=lambda _id: calculate_holdings(HOLDINGS_SOURCE)) as get_holdings:
        yield get_holdings


@pytest.fixture
def fx():
    with patch('portfolio.fx_service.fetch_pair_rate', return_value=dict(RATE)) as fetch:
        yield fetch


def test_portfolio_default_is_native_and_unchanged(client, crm, fx):
    body = client.get('/portfolios/P-9001').json()
    assert body['currency'] == 'CAD'
    assert body['totalMarketValue'] == 48930
    assert body['dayChangePercent'] == pytest.approx(0.0006134969325153374)
    assert (body['exchangeRate'], body['exchangeRateAsOf']) == (1, None)
    fx.assert_not_called()


def test_portfolio_in_usd_converts_money_only(client, crm, fx):
    response = client.get('/portfolios/P-9001?currency=%20usd%20')
    assert response.status_code == 200
    body = response.json()
    assert body['currency'] == 'USD'
    assert body['totalMarketValue'] == 34348.86
    assert body['dayChangeAmount'] == 21.06
    assert body['dayChangePercent'] == pytest.approx(0.0006134969325153374)
    assert body['totalReturnSinceInception'] == 0.187
    assert body['exchangeRate'] == 0.702
    assert body['exchangeRateAsOf'] == '2026-10-03T00:00:02.000Z'
    fx.assert_called_once_with('CAD', 'USD')


def test_unsupported_currency_is_400_without_crm_or_fx_call(client, crm, fx):
    response = client.get('/portfolios/P-9001?currency=EUR')
    assert response.status_code == 400
    assert response.json()['error'] == 'unsupported_currency'
    crm.assert_not_called()
    fx.assert_not_called()


def test_fx_unavailable_is_503(client, crm):
    with patch('portfolio.fx_service.fetch_pair_rate', side_effect=FxError('timeout')):
        response = client.get('/portfolios/P-9001?currency=USD')
    assert response.status_code == 503
    assert response.json()['error'] == 'fx_unavailable'


def test_cad_still_works_when_fx_is_down(client, crm):
    with patch('portfolio.fx_service.fetch_pair_rate', side_effect=FxError('timeout')) as fetch:
        response = client.get('/portfolios/P-9001?currency=CAD')
    assert response.status_code == 200
    fetch.assert_not_called()


def test_holdings_in_usd_stay_an_array_with_metadata(client, holdings, fx):
    body = client.get('/portfolios/P-9001/holdings?currency=USD').json()

    assert isinstance(body, list)
    aapl = body[0]
    assert aapl['currency'] == 'USD'
    assert aapl['exchangeRate'] == 0.702
    assert aapl['exchangeRateAsOf'] == '2026-10-03T00:00:02.000Z'
    assert aapl['marketValue'] == 19164.60
    assert aapl['price'] == 159.71
    assert aapl['costBasisPerShare'] == 140.40
    assert aapl['quantity'] == 120
    assert aapl['weightPercent'] == pytest.approx(27300 / 48930)


def test_holdings_default_has_native_metadata(client, holdings, fx):
    body = client.get('/portfolios/P-9001/holdings').json()
    assert body[0]['marketValue'] == 27300
    assert (body[0]['currency'], body[0]['exchangeRate'], body[0]['exchangeRateAsOf']) == ('CAD', 1, None)
    fx.assert_not_called()


def test_empty_holdings_in_usd_is_empty_array(client, fx):
    with patch('portfolio.services.get_holdings', return_value=[]):
        response = client.get('/portfolios/P-EMPTY/holdings?currency=USD')
    assert response.status_code == 200
    assert response.json() == []


def test_holdings_unsupported_currency_is_400_before_loading(client, holdings, fx):
    response = client.get('/portfolios/P-9001/holdings?currency=GBP')
    assert response.status_code == 400
    holdings.assert_not_called()


def test_converted_holdings_sum_matches_converted_portfolio_total(client, crm, holdings, fx):
    total = client.get('/portfolios/P-9001?currency=USD').json()['totalMarketValue']
    items = client.get('/portfolios/P-9001/holdings?currency=USD').json()
    assert abs(sum(h['marketValue'] for h in items) - total) <= 0.01 * len(items)
    assert fx.call_count == 1  # second request served from the daily cache
