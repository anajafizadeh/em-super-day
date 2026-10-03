"""Pure validation and calendar-range filtering for daily market values."""

from calendar import monthrange
from datetime import date
from decimal import Decimal
from math import isfinite

from constants import PERFORMANCE_RANGES


class InvalidRange(ValueError):
    """The requested range is not one of the API's supported values."""


class InvalidHistory(ValueError):
    """Stored snapshots do not match the daily-history schema."""


def validate_range(range_name):
    """Reject unknown, empty, or incorrectly cased range values."""
    if range_name not in PERFORMANCE_RANGES:
        raise InvalidRange(
            f"range must be one of: {', '.join(PERFORMANCE_RANGES)}."
        )


def _range_start(range_name, today):
    if range_name == "All":
        return date.min
    if range_name == "1D":
        return today
    if range_name == "YTD":
        return date(today.year, 1, 1)
    if range_name == "1M":
        year = today.year if today.month > 1 else today.year - 1
        month = today.month - 1 if today.month > 1 else 12
    else:  # 1Y
        year, month = today.year - 1, today.month
    day = min(today.day, monthrange(year, month)[1])
    return date(year, month, day)


def _snapshot(row, index):
    if not isinstance(row, dict):
        raise InvalidHistory(f"Snapshot {index} must be an object.")
    raw_date = row.get("date")
    if not isinstance(raw_date, str):
        raise InvalidHistory(f"Snapshot {index} must have a YYYY-MM-DD date.")
    try:
        snapshot_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise InvalidHistory(f"Snapshot {index} has an invalid date.") from exc
    if snapshot_date.isoformat() != raw_date:
        raise InvalidHistory(f"Snapshot {index} must have a YYYY-MM-DD date.")

    value = row.get("marketValue")
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise InvalidHistory(f"Snapshot {index} marketValue must be a number.")
    value = Decimal(str(value))
    if not value.is_finite():
        raise InvalidHistory(f"Snapshot {index} marketValue must be finite.")
    try:
        json_finite = isfinite(float(value))
    except OverflowError:
        json_finite = False
    if not json_finite:
        raise InvalidHistory(f"Snapshot {index} marketValue is too large.")
    return snapshot_date, {"date": raw_date, "marketValue": value}


def filter_performance_history(snapshots, range_name="All", *, today):
    """Return validated, sorted snapshots within inclusive calendar bounds.

    ``today`` is supplied by the caller, keeping clock and storage dependencies
    outside this module. Future snapshots are excluded even for ``All``.
    Input rows are never mutated, and missing dates are never synthesized.
    """
    validate_range(range_name)
    if type(today) is not date:
        raise ValueError("today must be a date.")
    if not isinstance(snapshots, list):
        raise InvalidHistory("Performance history must be an array.")
    start = _range_start(range_name, today)
    result = []
    seen_dates = set()
    for index, row in enumerate(snapshots):
        snapshot_date, normalized = _snapshot(row, index)
        if snapshot_date in seen_dates:
            raise InvalidHistory(f"Duplicate snapshot date: {snapshot_date}.")
        seen_dates.add(snapshot_date)
        if start <= snapshot_date <= today:
            result.append(normalized)
    return sorted(result, key=lambda snapshot: snapshot["date"])
