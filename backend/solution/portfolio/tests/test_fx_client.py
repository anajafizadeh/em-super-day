import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests

from constants import FX_MAX_RETRIES, FX_TIMEOUT_SECONDS
from portfolio.fx_client import FxError, fetch_pair_rate

KEY = 'test-secret-key-123'


def _body(**overrides):
    payload = {
        'result': 'success',
        'time_last_update_unix': 1790985602,
        'time_next_update_unix': 1791072002,
        'base_code': 'CAD',
        'target_code': 'USD',
        'conversion_rate': 0.7020,
    }
    payload.update(overrides)
    return json.dumps(payload)


def _response(status=200, text=None):
    return Mock(status_code=status, text=_body() if text is None else text)


@pytest.fixture
def mock_get(settings):
    settings.EXCHANGE_RATE_API_KEY = KEY
    with patch('portfolio.fx_client.requests.get') as get:
        yield get


def _kind(exc_info):
    return exc_info.value.kind


def test_success_parses_rate_and_times(mock_get):
    mock_get.return_value = _response()
    result = fetch_pair_rate('CAD', 'USD')

    assert result['rate'] == Decimal('0.7020')
    assert result['as_of'] == '2026-10-03T00:00:02.000Z'
    assert result['next_update'] == datetime(2026, 10, 4, 0, 0, 2, tzinfo=timezone.utc)
    mock_get.assert_called_once_with(
        f'https://v6.exchangerate-api.com/v6/{KEY}/pair/CAD/USD', timeout=FX_TIMEOUT_SECONDS
    )


@pytest.mark.parametrize('error_type', [
    'invalid-key', 'quota-reached', 'unsupported-code', 'malformed-request', 'inactive-account',
])
def test_provider_error_types_are_not_retried(mock_get, error_type):
    mock_get.return_value = _response(403, json.dumps({'result': 'error', 'error-type': error_type}))
    with pytest.raises(FxError) as exc_info:
        fetch_pair_rate('CAD', 'USD')
    assert _kind(exc_info) == f'provider_{error_type}'
    assert mock_get.call_count == 1


def test_5xx_then_success_retries_once(mock_get):
    mock_get.side_effect = [_response(503, ''), _response()]
    assert fetch_pair_rate('CAD', 'USD')['rate'] == Decimal('0.7020')
    assert mock_get.call_count == 2


def test_repeated_timeout_raises_after_retries(mock_get):
    mock_get.side_effect = requests.Timeout()
    with pytest.raises(FxError) as exc_info:
        fetch_pair_rate('CAD', 'USD')
    assert _kind(exc_info) == 'timeout'
    assert mock_get.call_count == 1 + FX_MAX_RETRIES


def test_repeated_connection_error_raises(mock_get):
    mock_get.side_effect = requests.ConnectionError()
    with pytest.raises(FxError) as exc_info:
        fetch_pair_rate('CAD', 'USD')
    assert _kind(exc_info) == 'connection_error'


def test_other_request_errors_are_not_retried(mock_get):
    mock_get.side_effect = requests.TooManyRedirects()
    with pytest.raises(FxError) as exc_info:
        fetch_pair_rate('CAD', 'USD')
    assert _kind(exc_info) == 'request_error'
    assert mock_get.call_count == 1


@pytest.mark.parametrize('text', [
    '<html>oops</html>',
    '[]',
    _body(result='weird'),
    _body(conversion_rate=0),
    _body(conversion_rate=-0.7),
    _body(conversion_rate='0.70'),
    _body(conversion_rate=True),
    _body(conversion_rate=None),
    _body(base_code='USD'),
    _body(target_code='EUR'),
    _body(time_next_update_unix='tomorrow'),
    _body(time_last_update_unix=None),
    _body(time_next_update_unix=10 ** 20),
    '{"result": "success", "conversion_rate": NaN}',
])
def test_invalid_payloads_are_rejected(mock_get, text):
    mock_get.return_value = _response(200, text)
    with pytest.raises(FxError) as exc_info:
        fetch_pair_rate('CAD', 'USD')
    assert _kind(exc_info) == 'invalid_payload'


def test_success_body_with_non_200_status_is_rejected(mock_get):
    mock_get.return_value = _response(404)
    with pytest.raises(FxError):
        fetch_pair_rate('CAD', 'USD')


def test_api_key_never_appears_in_logs(mock_get, caplog):
    mock_get.side_effect = requests.Timeout(f'timed out calling .../{KEY}/pair/CAD/USD')
    with caplog.at_level(logging.DEBUG), pytest.raises(FxError) as exc_info:
        fetch_pair_rate('CAD', 'USD')
    assert caplog.records  # the retry was logged
    assert KEY not in caplog.text
    assert KEY not in str(exc_info.value)
