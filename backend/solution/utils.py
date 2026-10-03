"""Shared helpers: the API error type, its JSON response, and a Decimal-aware encoder."""

import json
from decimal import Decimal

from django.http import JsonResponse


class ApiError(Exception):
    """An error that maps directly to a JSON response: {error, message} with `status`."""

    def __init__(self, status, error, message):
        super().__init__(message)
        self.status = status
        self.error = error
        self.message = message


def error_response(err):
    """Turn an ApiError into a JsonResponse with the shared error schema."""
    return JsonResponse({'error': err.error, 'message': err.message}, status=err.status)


class DecimalJSONEncoder(json.JSONEncoder):
    """Write Decimal as a JSON number. All maths stays Decimal; float is only the wire format."""

    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)
