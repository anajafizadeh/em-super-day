"""Task 2 orchestration: establish portfolio identity, load, and calculate."""

from portfolio.data import load_seed, require_portfolio
from portfolio.holdings import calculate_holdings
from utils import ApiError


def _select_holdings(seed, portfolio_id):
    if not isinstance(seed, dict) or not isinstance(seed.get("holdings"), list):
        raise ValueError("The holdings source must contain a holdings array.")
    selected = []
    for holding in seed["holdings"]:
        if not isinstance(holding, dict):
            raise ValueError("Each source holding must be an object.")
        owner = holding.get("portfolioId")
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError("Each source holding must identify its portfolio.")
        if owner == portfolio_id:
            selected.append(holding)
    return selected


def get_holdings(portfolio_id):
    """Calculate this portfolio's positions afresh on every request."""
    require_portfolio(portfolio_id)
    seed = load_seed()
    try:
        return calculate_holdings(_select_holdings(seed, portfolio_id))
    except ValueError as exc:
        raise ApiError(
            503, "data_unavailable", "Holdings data is unavailable or invalid."
        ) from exc
