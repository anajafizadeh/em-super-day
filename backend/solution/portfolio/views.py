from django.http import JsonResponse
from django.views.decorators.http import require_GET

from utils import ApiError, DecimalJSONEncoder, error_response

from .services import get_crm_data


@require_GET
def portfolio_detail(request, portfolio_id):
    try:
        return JsonResponse(get_crm_data(portfolio_id), encoder=DecimalJSONEncoder)
    except ApiError as err:
        return error_response(err)
