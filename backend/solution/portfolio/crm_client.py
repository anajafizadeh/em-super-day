"""HTTP access to the external CRM. No mapping here, only fetching and transport errors."""

import json
import logging
from decimal import Decimal
from urllib.parse import quote

import requests
from django.conf import settings

from constants import CRM_MAX_RETRIES, CRM_PORTFOLIO_PATH, CRM_TIMEOUT_SECONDS
from utils import ApiError

logger = logging.getLogger(__name__)


def _reject_constant(name):
    raise ValueError(f'Non-finite number {name} in CRM response')


def _parse_json(response):
    try:
        return json.loads(response.text, parse_float=Decimal, parse_constant=_reject_constant)
    except ValueError:
        raise ApiError(400, 'crm_bad_response', 'CRM returned a response that is not valid JSON.')


def fetch_crm_portfolio(portfolio_id):
    """Fetch the raw CRM payload for an already-normalized portfolio id.

    Retries timeouts, connection errors and 5xx up to CRM_MAX_RETRIES times.
    Raises ApiError: 404 portfolio_not_found, 400 crm_bad_response,
    502 crm_unavailable, or 504 crm_timeout.
    """
    url = settings.CRM_BASE_URL.rstrip('/') + CRM_PORTFOLIO_PATH.format(
        portfolio_id=quote(portfolio_id, safe='')
    )
    attempts = 1 + CRM_MAX_RETRIES
    last_failure = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=CRM_TIMEOUT_SECONDS)
        except requests.Timeout:
            last_failure = 'timeout'
        except requests.ConnectionError:
            last_failure = 'connection_error'
        else:
            if response.status_code >= 500:
                last_failure = f'http_{response.status_code}'
            elif response.status_code == 404:
                raise ApiError(404, 'portfolio_not_found', f'Portfolio {portfolio_id} was not found.')
            elif response.status_code != 200:
                raise ApiError(
                    400, 'crm_bad_response', f'CRM returned unexpected status {response.status_code}.'
                )
            else:
                return _parse_json(response)

        if attempt < attempts:
            logger.warning('CRM call for %s failed (%s), retrying (%d/%d)',
                           portfolio_id, last_failure, attempt, attempts)

    logger.warning('CRM call for %s failed after %d attempts (%s)', portfolio_id, attempts, last_failure)
    if last_failure == 'timeout':
        raise ApiError(504, 'crm_timeout', 'CRM did not respond in time.')
    raise ApiError(502, 'crm_unavailable', 'CRM is currently unavailable.')
