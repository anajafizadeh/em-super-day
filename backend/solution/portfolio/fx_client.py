"""HTTP access to ExchangeRate-API. No caching here, only fetching and validation.

The request URL contains the API key, so nothing here logs URLs or exception text.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import quote

import requests
from django.conf import settings

from constants import FX_BASE_URL, FX_MAX_RETRIES, FX_PAIR_PATH, FX_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class FxError(Exception):
    """The rate could not be fetched; `kind` is a short, key-free reason."""

    def __init__(self, kind):
        super().__init__(kind)
        self.kind = kind


def _reject_constant(name):
    raise ValueError('Non-finite number in FX response')


def _iso_utc(unix_seconds):
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).isoformat(
        timespec='milliseconds'
    ).replace('+00:00', 'Z')


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _parse(response, base, target):
    try:
        payload = json.loads(response.text, parse_float=Decimal, parse_constant=_reject_constant)
    except ValueError:
        raise FxError('invalid_payload')
    if not isinstance(payload, dict):
        raise FxError('invalid_payload')

    if payload.get('result') == 'error':
        error_type = payload.get('error-type')
        raise FxError(f'provider_{error_type}' if isinstance(error_type, str) else 'provider_error')
    if response.status_code != 200 or payload.get('result') != 'success':
        raise FxError('invalid_payload')
    if payload.get('base_code') != base or payload.get('target_code') != target:
        raise FxError('invalid_payload')

    rate = payload.get('conversion_rate')
    if isinstance(rate, bool) or not isinstance(rate, (int, Decimal)):
        raise FxError('invalid_payload')
    rate = Decimal(rate)
    if not rate.is_finite() or rate <= 0:
        raise FxError('invalid_payload')

    last_update = payload.get('time_last_update_unix')
    next_update = payload.get('time_next_update_unix')
    if not _is_int(last_update) or not _is_int(next_update):
        raise FxError('invalid_payload')
    try:
        return {
            'rate': rate,
            'as_of': _iso_utc(last_update),
            'next_update': datetime.fromtimestamp(next_update, tz=timezone.utc),
        }
    except (OverflowError, OSError, ValueError):
        raise FxError('invalid_payload')


def fetch_pair_rate(base, target):
    """Fetch the base->target rate: {rate: Decimal, as_of: ISO str, next_update: datetime}.

    Retries timeouts, connection errors and 5xx up to FX_MAX_RETRIES times.
    Provider errors (invalid-key, quota-reached, ...) are not retried. Raises FxError.
    """
    url = FX_BASE_URL + FX_PAIR_PATH.format(
        key=quote(settings.EXCHANGE_RATE_API_KEY, safe=''),
        base=quote(base, safe=''),
        target=quote(target, safe=''),
    )
    attempts = 1 + FX_MAX_RETRIES

    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=FX_TIMEOUT_SECONDS)
        except requests.Timeout:
            kind = 'timeout'
        except requests.ConnectionError:
            kind = 'connection_error'
        except requests.RequestException:
            raise FxError('request_error')
        else:
            if response.status_code < 500:
                return _parse(response, base, target)
            kind = f'http_{response.status_code}'

        if attempt < attempts:
            logger.warning('FX rate %s/%s failed (%s), retrying (%d/%d)',
                           base, target, kind, attempt, attempts)

    raise FxError(kind)
