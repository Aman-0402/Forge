"""Small pure helpers for settings modules, kept separate so they're unit-testable
without importing or reloading a full Django settings module."""

from django.core.exceptions import ImproperlyConfigured


def require_prod_settings(allowed_hosts, csrf_trusted_origins):
    """Fail fast if a production settings module is missing required env values.

    Both ``ALLOWED_HOSTS`` and ``CSRF_TRUSTED_ORIGINS`` default to an empty list when
    unset, which Django accepts silently but which leaves the app refusing every
    request (``DisallowedHost``) once ``DEBUG`` is off. Better to fail at startup.
    """
    missing = []
    if not any(host.strip() for host in allowed_hosts):
        missing.append("ALLOWED_HOSTS")
    if not any(origin.strip() for origin in csrf_trusted_origins):
        missing.append("CSRF_TRUSTED_ORIGINS")
    if missing:
        raise ImproperlyConfigured(
            f"Set {' and '.join(missing)} via environment variables before running "
            "with DEBUG=False (config/settings/prod.py)."
        )
