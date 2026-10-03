"""Task 3 orchestration: portfolio lookup, fixture loading, and filtering."""

from datetime import datetime, timezone

from django.conf import settings

from portfolio.data import load_json, require_portfolio
from portfolio.performance import (
    InvalidHistory,
    InvalidRange,
    filter_performance_history,
    validate_range,
)
from utils import ApiError


def utc_today():
    """Resolve the date for each request, independently of the host timezone."""
    return datetime.now(timezone.utc).date()


def get_performance_history(portfolio_id, range_name="All"):
    """Read and filter the portfolio's stored daily snapshots."""
    try:
        validate_range(range_name)
    except InvalidRange as exc:
        raise ApiError(400, "invalid_range", str(exc)) from exc

    require_portfolio(portfolio_id)
    path = getattr(
        settings,
        "PORTFOLIO_HISTORY_PATH",
        settings.BASE_DIR.parent / "fixtures" / "performance-history.json",
    )
    history = load_json(path)
    if not isinstance(history, dict) or portfolio_id not in history:
        raise ApiError(
            503,
            "data_unavailable",
            "Performance history is not available for this portfolio.",
        )
    try:
        return filter_performance_history(
            history[portfolio_id], range_name, today=utc_today()
        )
    except InvalidHistory as exc:
        raise ApiError(
            503, "data_unavailable", "Stored performance history is invalid."
        ) from exc
