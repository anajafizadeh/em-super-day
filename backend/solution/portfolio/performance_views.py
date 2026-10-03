"""Thin HTTP adapter for Task 3."""

from portfolio.performance_service import get_performance_history
from utils import api_get, json_response


@api_get
def performance_history(request, portfolio_id):
    result = get_performance_history(
        portfolio_id, request.GET.get("range", "All")
    )
    return json_response(result)
