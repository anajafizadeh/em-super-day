"""Thin HTTP adapters for portfolio endpoints."""

from portfolio.holdings_service import get_holdings
from portfolio.performance_service import get_performance_history
from portfolio.services import get_crm_data
from utils import api_get, json_response


@api_get
def portfolio_detail(request, portfolio_id):
    return json_response(get_crm_data(portfolio_id))


@api_get
def holdings(request, portfolio_id):
    return json_response(get_holdings(portfolio_id))


@api_get
def performance_history(request, portfolio_id):
    result = get_performance_history(
        portfolio_id, request.GET.get("range", "All")
    )
    return json_response(result)
