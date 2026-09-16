import json
import logging

from apps.core.logging import JsonFormatter


def make_record(**kwargs):
    defaults = dict(
        name="apps.core",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    defaults.update(kwargs)
    return logging.LogRecord(**defaults)


def test_formats_as_valid_json_with_expected_fields():
    record = make_record()
    record.request_id = "abc-123"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "apps.core"
    assert payload["request_id"] == "abc-123"
    assert "timestamp" in payload


def test_missing_request_id_defaults_to_dash():
    payload = json.loads(JsonFormatter().format(make_record()))
    assert payload["request_id"] == "-"


def test_exception_info_is_included():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = make_record(level=logging.ERROR, msg="failed", args=None, exc_info=sys.exc_info())
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]
