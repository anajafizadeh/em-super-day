"""Pure validation and mapping of CRM data into our portfolio schema.

No HTTP, storage or Django imports, so this is easy to unit test.
"""

import re
from datetime import datetime, timezone
from decimal import Decimal

from constants import NATIVE_CURRENCY, PORTFOLIO_ID_PATTERN
from utils import ApiError

# Monetary fields of the normalized portfolio; Task 7 converts exactly these.
MONEY_FIELDS = ('totalMarketValue', 'dayChangeAmount')

_MISSING = object()


def _bad_response(message):
    return ApiError(400, 'crm_bad_response', message)


def normalize_portfolio_id(raw):
    """Strip and uppercase the id, then check it against PORTFOLIO_ID_PATTERN."""
    portfolio_id = raw.strip().upper() if isinstance(raw, str) else ''
    if not re.fullmatch(PORTFOLIO_ID_PATTERN, portfolio_id):
        raise ApiError(400, 'invalid_portfolio_id', 'Invalid ID provided.')
    return portfolio_id


def _get(obj, *path):
    """Walk nested dicts; return _MISSING if any step is absent or not a dict."""
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return _MISSING
        obj = obj[key]
    return obj


def _required_str(value, field):
    if not isinstance(value, str) or not value.strip():
        raise _bad_response(f'CRM response is missing required field {field}.')
    return value.strip()


def _optional_str(value, field):
    if value is _MISSING or value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _bad_response(f'CRM field {field} must be a non-empty string.')
    return value.strip()


def _optional_number(value, field):
    if value is _MISSING or value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise _bad_response(f'CRM field {field} must be a number.')
    return Decimal(value)


def _optional_timestamp(value):
    """Parse an ISO 8601 datetime with a timezone; emit UTC with milliseconds, or None."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def _find_accounts(client_record):
    accounts = _get(client_record, 'accounts')
    if isinstance(accounts, list):
        return accounts
    accounts = _get(client_record, 'relationships', 'accounts')
    if isinstance(accounts, list):
        return accounts
    raise _bad_response('CRM response has no accounts list.')


def _find_account(accounts, portfolio_id):
    matches = []
    for account in accounts:
        if not isinstance(account, dict):
            raise _bad_response('CRM accounts list contains a non-object entry.')
        acct_ref = _required_str(account.get('acct_ref'), 'acct_ref')
        if acct_ref.upper() == portfolio_id:
            matches.append(account)
    if not matches:
        raise ApiError(404, 'portfolio_not_found', f'Portfolio {portfolio_id} was not found.')
    if len(matches) > 1:
        raise _bad_response(f'CRM returned more than one account for {portfolio_id}.')
    return matches[0]


def normalize_crm_portfolio(payload, portfolio_id):
    """Validate a raw CRM payload and map the requested account into our schema."""
    client_record = _get(payload, 'client_record')
    if not isinstance(client_record, dict):
        raise _bad_response('CRM response is missing client_record.')

    account = _find_account(_find_accounts(client_record), portfolio_id)

    client_id = _required_str(client_record.get('client_id'), 'client_id')
    currency = _required_str(_get(account, 'curr_val', 'ccy'), 'curr_val.ccy').upper()
    if currency != NATIVE_CURRENCY:
        raise _bad_response(f'CRM currency {currency} is not the native currency {NATIVE_CURRENCY}.')

    return {
        'portfolioId': portfolio_id,
        'clientId': client_id,
        'label': _optional_str(_get(account, 'acct_nickname'), 'acct_nickname'),
        'currency': currency,
        'totalMarketValue': _optional_number(_get(account, 'curr_val', 'amt'), 'curr_val.amt'),
        'dayChangeAmount': _optional_number(_get(account, 'chg_1d', 'amt'), 'chg_1d.amt'),
        'dayChangePercent': _optional_number(_get(account, 'chg_1d', 'pct'), 'chg_1d.pct'),
        'totalReturnSinceInception': _optional_number(
            _get(account, 'since_inception_pct'), 'since_inception_pct'
        ),
        'asOf': _optional_timestamp(_get(payload, 'meta', 'retrieved_at')),
    }
