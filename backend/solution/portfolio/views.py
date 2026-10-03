"""Thin HTTP adapters for portfolio endpoints."""

from portfolio.holdings_service import get_holdings
from utils import api_get, json_response


@api_get
def holdings(request, portfolio_id):
    return json_response(get_holdings(portfolio_id))
