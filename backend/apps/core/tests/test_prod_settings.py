"""Loads config/settings/prod.py directly (not via DJANGO_SETTINGS_MODULE) to check
it fails fast without production environment variables, and picks them up when set.
"""

import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured


def load_prod():
    sys.modules.pop("config.settings.prod", None)
    return importlib.import_module("config.settings.prod")


def test_prod_settings_raise_without_allowed_hosts_and_csrf_origins(monkeypatch):
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("CSRF_TRUSTED_ORIGINS", raising=False)
    with pytest.raises(ImproperlyConfigured):
        load_prod()


def test_prod_settings_load_with_both_set(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "forge.example.edu")
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "https://forge.example.edu")
    prod = load_prod()
    assert prod.ALLOWED_HOSTS == ["forge.example.edu"]
    assert prod.CSRF_TRUSTED_ORIGINS == ["https://forge.example.edu"]
    assert prod.DEBUG is False
    assert prod.LOGGING["formatters"]["console"] == {"()": "apps.core.logging.JsonFormatter"}
