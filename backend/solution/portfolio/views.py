"""Thin HTTP adapters for portfolio endpoints."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from portfolio.holdings_service import get_holdings
from portfolio.services import get_crm_data
from utils import ApiError, DecimalJSONEncoder, api_get, error_response, json_response


@require_GET
def portfolio_detail(request, portfolio_id):
    try:
        return JsonResponse(get_crm_data(portfolio_id), encoder=DecimalJSONEncoder)
    except ApiError as err:
        return error_response(err)


@api_get
def holdings(request, portfolio_id):
    return json_response(get_holdings(portfolio_id))
