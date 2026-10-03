"""Pure currency validation and money conversion (Task 7).

No HTTP, storage or Django imports, so this is easy to unit test.
"""

from decimal import ROUND_HALF_UP

from constants import MONEY_QUANTUM, NATIVE_CURRENCY, SUPPORTED_CURRENCIES
from utils import ApiError

# Monetary fields of a Task 2 holding; Task 7 converts exactly these.
HOLDING_MONEY_FIELDS = (
    'price', 'costBasisPerShare', 'previousClosePrice',
    'marketValue', 'unrealizedGainLoss', 'dayChangeAmount',
)


def normalize_currency(raw):
    """Strip and uppercase ?currency; missing or blank means the native currency."""
    if raw is None:
        return NATIVE_CURRENCY
    code = raw.strip().upper() if isinstance(raw, str) else None
    if code == '':
        return NATIVE_CURRENCY
    if code not in SUPPORTED_CURRENCIES:
        raise ApiError(
            400, 'unsupported_currency',
            f'Currency must be one of: {", ".join(SUPPORTED_CURRENCIES)}.',
        )
    return code


def convert_amount(amount, rate):
    """Convert a Decimal amount and round to cents; None stays None."""
    if amount is None:
        return None
    return (amount * rate).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def convert_record(record, money_fields, rate):
    """Return a copy of record with only money_fields converted."""
    converted = dict(record)
    for field in money_fields:
        if field in converted:
            converted[field] = convert_amount(converted[field], rate)
    return converted
