"""Integration tests against the real mock CRM (node backend/mock-crm.mjs).

Skipped automatically if the mock is not reachable at CRM_BASE_URL.
Each test forces the mock's global mode via POST /__control and restores 'auto'.
"""

import time

import pytest
import requests
from django.conf import settings

from portfolio.services import get_crm_data
from utils import ApiError

pytestmark = pytest.mark.integration


def _crm(path):
    return settings.CRM_BASE_URL.rstrip('/') + path


@pytest.fixture(scope='module', autouse=True)
def require_mock_crm():
    try:
        requests.get(_crm('/health'), timeout=1).raise_for_status()
    except requests.RequestException:
        pytest.skip(f'Mock CRM not reachable at {settings.CRM_BASE_URL}; run node backend/mock-crm.mjs')


@pytest.fixture
def crm_mode():
    def set_mode(mode):
        requests.post(_crm('/__control'), json={'mode': mode}, timeout=2).raise_for_status()
    yield set_mode
    set_mode('auto')


def _calls_for(portfolio_id):
    stats = requests.get(_crm('/__stats'), timeout=2).json()
    return stats['callsByPortfolio'].get(portfolio_id, 0)


def test_ok_mode_maps_requested_account(crm_mode):
    crm_mode('ok')
    result = get_crm_data(' p-9002 ')
    assert result['portfolioId'] == 'P-9002'
    assert result['clientId'] == 'abc123'
    assert result['label'] == 'Retirement Account'
    assert result['currency'] == 'CAD'
    assert result['asOf'].endswith('Z')


def test_nested_mode_maps_same_as_ok(crm_mode):
    crm_mode('ok')
    ok = get_crm_data('P-9001')
    crm_mode('nested')
    nested = get_crm_data('P-9001')
    assert {k: v for k, v in nested.items() if k != 'asOf'} == {k: v for k, v in ok.items() if k != 'asOf'}


def test_missing_mode_returns_nulls(crm_mode):
    crm_mode('missing')
    result = get_crm_data('P-9001')
    assert result['totalMarketValue'] is None
    assert result['label'] is None
    assert result['portfolioId'] == 'P-9001'


def test_unknown_id_is_404(crm_mode):
    crm_mode('ok')
    with pytest.raises(ApiError) as exc_info:
        get_crm_data('UNKNOWN')
    assert (exc_info.value.status, exc_info.value.error) == (404, 'portfolio_not_found')


def test_error_mode_retries_once_then_502(crm_mode):
    crm_mode('error')
    before = _calls_for('P-SINGLE')
    with pytest.raises(ApiError) as exc_info:
        get_crm_data('P-SINGLE')
    assert (exc_info.value.status, exc_info.value.error) == (502, 'crm_unavailable')
    assert _calls_for('P-SINGLE') - before == 2


def test_timeout_mode_gives_up_well_before_10s(crm_mode):
    crm_mode('timeout')
    started = time.monotonic()
    with pytest.raises(ApiError) as exc_info:
        get_crm_data('P-9001')
    elapsed = time.monotonic() - started
    assert (exc_info.value.status, exc_info.value.error) == (504, 'crm_timeout')
    assert elapsed < 6


def test_usd_end_to_end_with_real_crm(client, crm_mode):
    from datetime import datetime, timezone
    from decimal import Decimal
    from unittest.mock import patch

    crm_mode('ok')
    rate = {'rate': Decimal('0.7020'), 'as_of': '2026-10-03T00:00:02.000Z',
            'next_update': datetime(2099, 1, 1, tzinfo=timezone.utc)}
    with patch('portfolio.fx_service.fetch_pair_rate', return_value=rate):
        response = client.get('/portfolios/p-9001?currency=usd')

    assert response.status_code == 200
    body = response.json()
    assert body['portfolioId'] == 'P-9001'
    assert body['currency'] == 'USD'
    assert body['totalMarketValue'] == 34348.86  # 48930 CAD x 0.7020
    assert body['exchangeRate'] == 0.702
