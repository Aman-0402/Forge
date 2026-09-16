from django.core.exceptions import ImproperlyConfigured

from apps.core.settings_utils import require_prod_settings

from .base import *  # noqa: F401,F403
from .base import LOGGING, env

DEBUG = False

# Re-read from the environment rather than inheriting base's/dev's defaults: running
# with DEBUG=False and an empty ALLOWED_HOSTS silently refuses every request.
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
require_prod_settings(ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Structured JSON logs, still stamped with the request id (apps/core/logging.py).
LOGGING["formatters"]["console"] = {"()": "apps.core.logging.JsonFormatter"}

# Optional error tracking. Set SENTRY_DSN and install the `sentry` extra to enable.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError as exc:
        raise ImproperlyConfigured(
            "SENTRY_DSN is set but sentry-sdk is not installed. Run `uv sync --extra sentry`."
        ) from exc
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
