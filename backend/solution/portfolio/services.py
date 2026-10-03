"""Task orchestration. One main function per task, built from small helpers."""

from .crm_client import fetch_crm_portfolio
from .normalizers import normalize_crm_portfolio, normalize_portfolio_id


def get_crm_data(portfolio_id):
    """Fetch, validate and normalize one portfolio's CRM metadata (Task 1 schema).

    The single entry point for CRM data; Task 9 caches it and Task 7 converts it.
    Raises ApiError on invalid id, unknown portfolio, or CRM failure.
    """
    portfolio_id = normalize_portfolio_id(portfolio_id)
    payload = fetch_crm_portfolio(portfolio_id)
    return normalize_crm_portfolio(payload, portfolio_id)
