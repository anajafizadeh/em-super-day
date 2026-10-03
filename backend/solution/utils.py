"""Shared JSON responses and explicit API errors for portfolio endpoints."""

from decimal import Decimal
from functools import wraps
import math

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse


class ApiError(Exception):
    """An expected failure with a public status, code, and explanation."""

    def __init__(self, status, error, message):
        super().__init__(message)
        self.status = status
        self.error = error
        self.message = message


class DecimalJSONEncoder(DjangoJSONEncoder):
    """Keep Decimal calculations as JSON numbers at the response boundary."""

    def default(self, value):
        if isinstance(value, Decimal):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError('API numbers must be finite.')
            return number
        return super().default(value)


def json_response(data, *, status=200):
    return JsonResponse(
        data,
        safe=not isinstance(data, list),
        status=status,
        encoder=DecimalJSONEncoder,
        json_dumps_params={'allow_nan': False},
    )


def error_response(error):
    return json_response(
        {'error': error.error, 'message': error.message}, status=error.status
    )


def api_get(view):
    """Allow read-only requests and translate known domain errors to JSON."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method not in ('GET', 'HEAD'):
            response = error_response(ApiError(
                405, 'method_not_allowed', 'Use GET or HEAD for this endpoint.'
            ))
            response['Allow'] = 'GET, HEAD'
            return response
        try:
            return view(request, *args, **kwargs)
        except ApiError as error:
            return error_response(error)
    return wrapped


def not_found(request, exception):
    return error_response(ApiError(404, 'not_found', 'The requested resource was not found.'))


def server_error(request):
    return error_response(ApiError(500, 'internal_error', 'An unexpected server error occurred.'))
