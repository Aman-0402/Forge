"""Uniform API error envelope: {"detail": str, "code": str, "errors": dict}."""

from rest_framework import exceptions
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        errors = (
            response.data
            if isinstance(response.data, dict)
            else {"non_field_errors": response.data}
        )
        response.data = {
            "detail": "Invalid input.",
            "code": "validation_error",
            "errors": errors,
        }
        return response

    data = response.data if isinstance(response.data, dict) else {}
    detail = data.get("detail", str(exc))
    code = getattr(detail, "code", None) or getattr(exc, "default_code", "error")
    extra = {k: v for k, v in data.items() if k != "detail"}
    response.data = {"detail": str(detail), "code": str(code), "errors": extra}
    return response
