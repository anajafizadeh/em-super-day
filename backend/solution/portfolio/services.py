"""Task orchestration. One main function per task, built from small helpers."""

from .crm_client import fetch_crm_portfolio
from .currency import HOLDING_MONEY_FIELDS, normalize_currency
from .fx_service import apply_currency
from .holdings_service import get_holdings
from .normalizers import MONEY_FIELDS, normalize_crm_portfolio, normalize_portfolio_id


def get_crm_data(portfolio_id):
    """Fetch, validate and normalize one portfolio's CRM metadata (Task 1 schema).

    The single entry point for CRM data; Task 9 caches it and Task 7 converts it.
    Raises ApiError on invalid id, unknown portfolio, or CRM failure.
    """
    portfolio_id = normalize_portfolio_id(portfolio_id)
    payload = fetch_crm_portfolio(portfolio_id)
    return normalize_crm_portfolio(payload, portfolio_id)


def get_portfolio(portfolio_id, currency=None):
    """GET /portfolios/:id: Task 1 metadata in the requested display currency (Task 7)."""
    currency = normalize_currency(currency)
    return apply_currency(get_crm_data(portfolio_id), MONEY_FIELDS, currency)


def get_portfolio_holdings(portfolio_id, currency=None):
    """GET /portfolios/:id/holdings: Task 2 positions in the requested display currency."""
    currency = normalize_currency(currency)
    return apply_currency(get_holdings(portfolio_id), HOLDING_MONEY_FIELDS, currency)
