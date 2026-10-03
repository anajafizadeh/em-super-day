from decimal import Decimal
from unittest.mock import patch

import pytest

from utils import ApiError

NORMALIZED = {
    'portfolioId': 'P-9001',
    'clientId': 'abc123',
    'label': None,
    'currency': 'CAD',
    'totalMarketValue': Decimal('482350.12'),
    'dayChangeAmount': Decimal('1520.44'),
    'dayChangePercent': Decimal('0.0032'),
    'totalReturnSinceInception': Decimal('0.187'),
    'asOf': '2025-06-01T10:00:00.000Z',
}


def test_success_returns_schema_with_json_numbers(client):
    with patch('portfolio.services.get_crm_data', return_value=NORMALIZED) as get_crm_data:
        response = client.get('/portfolios/p-9001')

    assert response.status_code == 200
    body = response.json()
    assert body['totalMarketValue'] == 482350.12
    assert isinstance(body['totalMarketValue'], float)
    assert body['label'] is None
    assert body['asOf'] == '2025-06-01T10:00:00.000Z'
    get_crm_data.assert_called_once_with('p-9001')


@pytest.mark.parametrize('err', [
    ApiError(404, 'portfolio_not_found', 'Portfolio P-0000 was not found.'),
    ApiError(400, 'crm_bad_response', 'CRM response is missing client_record.'),
    ApiError(502, 'crm_unavailable', 'CRM is currently unavailable.'),
    ApiError(504, 'crm_timeout', 'CRM did not respond in time.'),
])
def test_api_errors_map_to_status_and_body(client, err):
    with patch('portfolio.services.get_crm_data', side_effect=err):
        response = client.get('/portfolios/P-9001')

    assert response.status_code == err.status
    assert response.json() == {'error': err.error, 'message': err.message}


def test_invalid_id_is_400_without_calling_crm(client):
    with patch('portfolio.crm_client.requests.get') as mock_get:
        response = client.get('/portfolios/bad!id')

    assert response.status_code == 400
    assert response.json() == {'error': 'invalid_portfolio_id', 'message': 'Invalid ID provided.'}
    mock_get.assert_not_called()


def test_non_get_is_json_405(client):
    response = client.post('/portfolios/P-9001')
    assert response.status_code == 405
    assert response.json()['error'] == 'method_not_allowed'
    assert response['Allow'] == 'GET, HEAD'
