"""Request-ID tracing: one ID per request, in the response header and every log line.

Downstream services and browsers can pass ``X-Request-ID`` in; if it looks safe it is
reused (so a request can be traced end to end through a reverse proxy), otherwise a
fresh one is generated. The ID lives in a contextvar for the life of the request so
:class:`RequestIDFilter` can stamp it onto every log record emitted while handling it,
without threading it through every function call.
"""

import logging
import re
import uuid
from contextvars import ContextVar

HEADER_IN = "HTTP_X_REQUEST_ID"
HEADER_OUT = "X-Request-ID"
_VALID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

_current: ContextVar[str] = ContextVar("request_id", default="-")


def current_request_id():
    return _current.get()


def _new_id():
    return uuid.uuid4().hex


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get(HEADER_IN, "")
        request_id = incoming if _VALID.match(incoming) else _new_id()
        request.request_id = request_id
        token = _current.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _current.reset(token)
        response[HEADER_OUT] = request_id
        return response


class RequestIDFilter(logging.Filter):
    """Logging filter that stamps the active request's id onto every record."""

    def filter(self, record):
        record.request_id = current_request_id()
        return True
