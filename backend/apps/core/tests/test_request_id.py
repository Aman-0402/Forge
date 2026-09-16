import logging
import re

from django.conf import settings

from apps.core.middleware import RequestIDFilter, current_request_id

UUID_HEX = re.compile(r"^[0-9a-f]{32}$")


def test_response_gets_a_generated_request_id(client):
    res = client.get("/no-such-path/")
    assert res.status_code == 404
    assert UUID_HEX.match(res["X-Request-ID"])


def test_valid_incoming_request_id_is_echoed_back(client):
    res = client.get("/no-such-path/", HTTP_X_REQUEST_ID="trace-abc-123")
    assert res["X-Request-ID"] == "trace-abc-123"


def test_malformed_incoming_request_id_is_replaced(client):
    res = client.get("/no-such-path/", HTTP_X_REQUEST_ID="not valid\nheader")
    assert res["X-Request-ID"] != "not valid\nheader"
    assert UUID_HEX.match(res["X-Request-ID"])


def test_request_id_available_during_the_request_and_cleared_after(client):
    assert current_request_id() == "-"
    client.get("/no-such-path/", HTTP_X_REQUEST_ID="during-request")
    # The middleware resets the contextvar once the response has been built.
    assert current_request_id() == "-"


def test_filter_attaches_current_request_id_to_log_records():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "hi", None, None)
    RequestIDFilter().filter(record)
    assert record.request_id == "-"


def test_middleware_runs_first():
    assert settings.MIDDLEWARE[0] == "apps.core.middleware.RequestIDMiddleware"
