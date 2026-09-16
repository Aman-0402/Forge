import pytest

TOKEN = "/api/v1/auth/token/"


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5175"],
)
def test_dev_cors_allows_any_local_vite_port(client, origin):
    res = client.options(
        TOKEN,
        HTTP_ORIGIN=origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
    )
    assert res.headers.get("Access-Control-Allow-Origin") == origin


def test_dev_cors_rejects_non_local_origin(client):
    res = client.options(
        TOKEN,
        HTTP_ORIGIN="http://evil.example.com",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )
    assert "Access-Control-Allow-Origin" not in res.headers
