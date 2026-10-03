"""Thin HTTP adapters for portfolio endpoints."""

from portfolio.performance_service import get_performance_history
from portfolio.services import get_portfolio, get_portfolio_holdings
from utils import api_get, json_response


@api_get
def portfolio_detail(request, portfolio_id):
    return json_response(get_portfolio(portfolio_id, request.GET.get('currency')))


@api_get
def holdings(request, portfolio_id):
    return json_response(get_portfolio_holdings(portfolio_id, request.GET.get('currency')))


@api_get
def performance_history(request, portfolio_id):
    result = get_performance_history(
        portfolio_id, request.GET.get("range", "All")
    )
    return json_response(result)
