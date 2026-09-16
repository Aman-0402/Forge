import pytest

from apps.audit.models import AuditLog

URL = "/api/v1/site-settings/"

pytestmark = pytest.mark.django_db


def test_public_can_read_settings_without_auth(api_client):
    res = api_client.get(URL)
    assert res.status_code == 200
    assert res.data == {
        "registration_open": True,
        "maintenance_mode": False,
        "maintenance_message": "",
    }


def test_admin_can_update_settings(auth_client, admin_user, api_client):
    res = auth_client(admin_user).patch(
        URL,
        {
            "registration_open": False,
            "maintenance_mode": True,
            "maintenance_message": "Down for upgrades.",
        },
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data == {
        "registration_open": False,
        "maintenance_mode": True,
        "maintenance_message": "Down for upgrades.",
    }
    # A second read (as anyone) sees the update — it's a real singleton, not per-request.
    assert api_client.get(URL).data["maintenance_mode"] is True
    assert AuditLog.objects.filter(action="site_settings.update").exists()


def test_non_admin_cannot_update_settings(auth_client, student_user, faculty_user):
    assert student_user and faculty_user
    body = {"registration_open": False}
    assert auth_client(student_user).patch(URL, body, format="json").status_code == 403
    assert auth_client(faculty_user).patch(URL, body, format="json").status_code == 403


def test_anonymous_cannot_update_settings(api_client):
    assert api_client.patch(URL, {"registration_open": False}, format="json").status_code in (
        401,
        403,
    )


def test_partial_update_keeps_other_fields(auth_client, admin_user):
    admin = auth_client(admin_user)
    admin.patch(URL, {"maintenance_mode": True}, format="json")
    res = admin.patch(URL, {"maintenance_message": "brb"}, format="json")
    assert res.data == {
        "registration_open": True,
        "maintenance_mode": True,
        "maintenance_message": "brb",
    }
