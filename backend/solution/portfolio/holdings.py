"""Pure validation and valuation of a portfolio's current positions."""

from decimal import Decimal, DecimalException, localcontext


_TEXT_FIELDS = ("ticker", "name", "assetClass")
_NUMBER_FIELDS = ("quantity", "costBasisPerShare", "price", "previousClosePrice")
_ZERO = Decimal(0)


def _number(value, field):
    """Normalize JSON numbers without introducing binary floating-point error."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"Holding {field} must be a finite number.")
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError(f"Holding {field} must be a finite number.")
    return number


def _normalize_holding(holding):
    if not isinstance(holding, dict):
        raise ValueError("Each holding must be an object.")
    result = {}
    for field in _TEXT_FIELDS:
        value = holding.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Holding {field} must be a non-empty string.")
        result[field] = value
    for field in _NUMBER_FIELDS:
        result[field] = _number(holding.get(field), field)
    return result


def calculate_holdings(holdings):
    """Return newly calculated positions, with decimal ratios and no rounding.

    The denominator is the sum of current position values. Zero denominators
    yield zero ratios. Day-change percent measures the security's price change,
    including when the held quantity is zero. Stored derived fields are ignored.
    """
    if not isinstance(holdings, list):
        raise ValueError("Holdings must be an array.")
    try:
        with localcontext() as context:
            context.prec = 28
            positions = [_normalize_holding(holding) for holding in holdings]
            for position in positions:
                position["marketValue"] = position["quantity"] * position["price"]
            total = sum((position["marketValue"] for position in positions), _ZERO)
            for position in positions:
                quantity = position["quantity"]
                price = position["price"]
                previous_close = position["previousClosePrice"]
                position["weightPercent"] = (
                    position["marketValue"] / total if total else _ZERO
                )
                position["unrealizedGainLoss"] = (
                    price - position["costBasisPerShare"]
                ) * quantity
                position["dayChangeAmount"] = (price - previous_close) * quantity
                position["dayChangePercent"] = (
                    (price - previous_close) / previous_close
                    if previous_close
                    else _ZERO
                )
            return positions
    except DecimalException as exc:
        raise ValueError("Holding numbers exceed the supported decimal range.") from exc
