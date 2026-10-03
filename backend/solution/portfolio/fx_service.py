"""Task 7 orchestration: daily-cached live rates and response conversion."""

import logging
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from constants import FX_FAILURE_COOLDOWN_SECONDS, NATIVE_CURRENCY
from utils import ApiError

from .currency import convert_record
from .fx_client import FxError, fetch_pair_rate

logger = logging.getLogger(__name__)

# Process-local cache: target currency -> {rate, as_of, next_update}.
_lock = threading.Lock()
_rates = {}
_failed_at = {}


def _now():
    return datetime.now(timezone.utc)


def reset_cache():
    """Forget cached rates and failures (used by tests)."""
    with _lock:
        _rates.clear()
        _failed_at.clear()


def _public(entry):
    return {'rate': entry['rate'], 'as_of': entry['as_of']}


def get_exchange_rate(target):
    """Return {rate, as_of} to convert from the native currency to `target`.

    Fresh rates are reused until the provider's next update. On failure the last
    good rate is served; with none, raise ApiError 503 fx_unavailable. After a
    failed refresh the provider is not called again for FX_FAILURE_COOLDOWN_SECONDS.
    """
    if target == NATIVE_CURRENCY:
        return {'rate': Decimal(1), 'as_of': None}

    with _lock:
        now = _now()
        cached = _rates.get(target)
        if cached and now < cached['next_update']:
            return _public(cached)

        failed_at = _failed_at.get(target)
        if failed_at is None or now - failed_at >= timedelta(seconds=FX_FAILURE_COOLDOWN_SECONDS):
            try:
                fresh = fetch_pair_rate(NATIVE_CURRENCY, target)
            except FxError as err:
                _failed_at[target] = now
                logger.warning('FX refresh %s/%s failed (%s); using fallback',
                               NATIVE_CURRENCY, target, err.kind)
            else:
                # Guard against a provider next-update time already in the past,
                # which would otherwise trigger a call on every request.
                min_next = now + timedelta(seconds=FX_FAILURE_COOLDOWN_SECONDS)
                fresh['next_update'] = max(fresh['next_update'], min_next)
                _rates[target] = fresh
                _failed_at.pop(target, None)
                return _public(fresh)

        if cached:
            return _public(cached)
    raise ApiError(503, 'fx_unavailable', 'Exchange rates are currently unavailable.')


def apply_currency(data, money_fields, target):
    """Convert a record (or list of records) to `target` and add currency metadata."""
    fx = get_exchange_rate(target)
    metadata = {'currency': target, 'exchangeRate': fx['rate'], 'exchangeRateAsOf': fx['as_of']}

    def convert(record):
        if target != NATIVE_CURRENCY:
            record = convert_record(record, money_fields, fx['rate'])
        return {**record, **metadata}

    if isinstance(data, list):
        return [convert(record) for record in data]
    return convert(data)
