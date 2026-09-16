import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.core.settings_utils import require_prod_settings


def test_passes_when_both_are_set():
    require_prod_settings(["forge.example.edu"], ["https://forge.example.edu"])


def test_raises_when_allowed_hosts_missing():
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS"):
        require_prod_settings([], ["https://forge.example.edu"])


def test_raises_when_csrf_trusted_origins_missing():
    with pytest.raises(ImproperlyConfigured, match="CSRF_TRUSTED_ORIGINS"):
        require_prod_settings(["forge.example.edu"], [])


def test_blank_entries_do_not_count_as_set():
    with pytest.raises(ImproperlyConfigured):
        require_prod_settings([""], [" "])


def test_message_lists_both_when_both_missing():
    with pytest.raises(ImproperlyConfigured, match="ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS"):
        require_prod_settings([], [])
