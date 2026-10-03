from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests

from constants import CRM_MAX_RETRIES, CRM_TIMEOUT_SECONDS
from portfolio.crm_client import fetch_crm_portfolio
from utils import ApiError

OK_BODY = '{"client_record": {"accounts": []}, "meta": {"amt": 482350.12}}'


def _response(status, text=OK_BODY):
    return Mock(status_code=status, text=text)


@pytest.fixture
def mock_get():
    with patch('portfolio.crm_client.requests.get') as get:
        yield get


def test_success_returns_parsed_json_with_decimals(mock_get, settings):
    settings.CRM_BASE_URL = 'http://crm.test/'
    mock_get.return_value = _response(200)

    payload = fetch_crm_portfolio('P-9001')

    assert payload['meta']['amt'] == Decimal('482350.12')
    mock_get.assert_called_once_with(
        'http://crm.test/crm/portfolios/P-9001', timeout=CRM_TIMEOUT_SECONDS
    )


def test_id_is_url_quoted(mock_get, settings):
    settings.CRM_BASE_URL = 'http://crm.test'
    mock_get.return_value = _response(200)
    fetch_crm_portfolio('A/B?C')
    assert mock_get.call_args.args[0] == 'http://crm.test/crm/portfolios/A%2FB%3FC'


def test_5xx_then_success_retries_once(mock_get):
    mock_get.side_effect = [_response(503), _response(200)]
    assert fetch_crm_portfolio('P-9001')['client_record'] == {'accounts': []}
    assert mock_get.call_count == 2


def test_timeout_then_success_retries_once(mock_get):
    mock_get.side_effect = [requests.Timeout(), _response(200)]
    fetch_crm_portfolio('P-9001')
    assert mock_get.call_count == 2


def test_repeated_timeout_is_504(mock_get):
    mock_get.side_effect = requests.Timeout()
    with pytest.raises(ApiError) as exc_info:
        fetch_crm_portfolio('P-9001')
    assert (exc_info.value.status, exc_info.value.error) == (504, 'crm_timeout')
    assert mock_get.call_count == 1 + CRM_MAX_RETRIES


def test_repeated_5xx_is_502(mock_get):
    mock_get.return_value = _response(503)
    with pytest.raises(ApiError) as exc_info:
        fetch_crm_portfolio('P-9001')
    assert (exc_info.value.status, exc_info.value.error) == (502, 'crm_unavailable')
    assert mock_get.call_count == 1 + CRM_MAX_RETRIES


def test_repeated_connection_error_is_502(mock_get):
    mock_get.side_effect = requests.ConnectionError()
    with pytest.raises(ApiError) as exc_info:
        fetch_crm_portfolio('P-9001')
    assert (exc_info.value.status, exc_info.value.error) == (502, 'crm_unavailable')


def test_404_is_not_found_and_not_retried(mock_get):
    mock_get.return_value = _response(404, '{"error": "unknown_account"}')
    with pytest.raises(ApiError) as exc_info:
        fetch_crm_portfolio('P-0000')
    assert (exc_info.value.status, exc_info.value.error) == (404, 'portfolio_not_found')
    assert mock_get.call_count == 1


def test_other_4xx_is_bad_response_and_not_retried(mock_get):
    mock_get.return_value = _response(400, '{"error": "bad_request"}')
    with pytest.raises(ApiError) as exc_info:
        fetch_crm_portfolio('P-9001')
    assert (exc_info.value.status, exc_info.value.error) == (400, 'crm_bad_response')
    assert mock_get.call_count == 1


@pytest.mark.parametrize('body', ['<html>oops</html>', '', '{"amt": NaN}', '{"amt": Infinity}'])
def test_invalid_json_is_bad_response_and_not_retried(mock_get, body):
    mock_get.return_value = _response(200, body)
    with pytest.raises(ApiError) as exc_info:
        fetch_crm_portfolio('P-9001')
    assert (exc_info.value.status, exc_info.value.error) == (400, 'crm_bad_response')
    assert mock_get.call_count == 1
