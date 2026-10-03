"""Local fixture storage and the integration boundary for Task 1 metadata."""

from decimal import Decimal
import json

from django.conf import settings
from django.utils.module_loading import import_string

from utils import ApiError


def _reject_constant(value):
    raise ValueError('JSON numbers must be finite.')


def load_json(path):
    """Read on each request so local data changes do not leave stale results."""
    try:
        with open(path, encoding='utf-8') as source:
            data = json.load(source, parse_float=Decimal, parse_constant=_reject_constant)
    except (OSError, UnicodeError, ValueError) as error:
        raise ApiError(
            503, 'data_unavailable', 'Portfolio data is unavailable or invalid.'
        ) from error
    if not isinstance(data, dict):
        raise ApiError(503, 'data_unavailable', 'Portfolio data must be a JSON object.')
    return data


def load_seed():
    return load_json(getattr(
        settings, 'PORTFOLIO_SEED_PATH',
        settings.BASE_DIR.parent / 'fixtures' / 'seed.json',
    ))


def require_portfolio(portfolio_id):
    """Check identity through get_crm_data, or the local seed until it is supplied.

    GET_CRM_DATA_CALLABLE names the teammate's importable function. It accepts
    portfolio_id and returns Task 1's mapped dictionary or raises ApiError.
    Only portfolioId is needed here; valuation is derived from local holdings.
    """
    provider_path = getattr(settings, 'GET_CRM_DATA_CALLABLE', '')
    if provider_path:
        metadata = import_string(provider_path)(portfolio_id)
        if not isinstance(metadata, dict) or metadata.get('portfolioId') != portfolio_id:
            raise ApiError(
                502, 'invalid_crm_data', 'CRM metadata does not match the requested portfolio.'
            )
        return metadata

    portfolios = load_seed().get('portfolios')
    if not isinstance(portfolios, list) or any(
        not isinstance(row, dict)
        or not isinstance(row.get('portfolioId'), str)
        or not row['portfolioId']
        for row in portfolios
    ):
        raise ApiError(503, 'data_unavailable', 'The portfolio registry is invalid.')
    for portfolio in portfolios:
        if portfolio['portfolioId'] == portfolio_id:
            return portfolio
    raise ApiError(404, 'portfolio_not_found', 'The requested portfolio was not found.')
