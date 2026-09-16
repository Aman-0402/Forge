from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from apps.accounts.tests.factories import UserFactory

User = get_user_model()
API = "/api/v1"
SET = f"{API}/auth/password/set/"
FORGOT = f"{API}/auth/password/forgot/"

pytestmark = pytest.mark.django_db


def link_params(link):
    query = parse_qs(urlparse(link).query)
    return query["uid"][0], query["token"][0]


def test_admin_create_sends_invite_link_not_password(auth_client, admin_user, api_client, settings):
    settings.FRONTEND_URL = "https://lms.example.edu"
    res = auth_client(admin_user).post(
        f"{API}/users/", {"email": "invitee@forge.test", "role": "faculty"}, format="json"
    )
    assert res.status_code == 201, res.data
    assert "temp_password" not in res.data
    link = res.data["invite_link"]
    assert link.startswith("https://lms.example.edu/set-password?")
    user = User.objects.get(email="invitee@forge.test")
    assert not user.has_usable_password()
    assert mail.outbox and link in mail.outbox[0].body
    assert "password:" not in mail.outbox[0].body.lower()

    uid, token = link_params(link)
    res = api_client.post(
        SET, {"uid": uid, "token": token, "new_password": "Chosen-Pass#2026"}, format="json"
    )
    assert res.status_code == 200, res.data
    assert {"access", "refresh"} <= res.data.keys()
    user.refresh_from_db()
    assert user.check_password("Chosen-Pass#2026")

    reused = api_client.post(
        SET, {"uid": uid, "token": token, "new_password": "Other-Pass#2026"}, format="json"
    )
    assert reused.status_code == 400


def test_invalid_link_and_weak_password_rejected(api_client, auth_client, admin_user):
    res = auth_client(admin_user).post(
        f"{API}/users/", {"email": "w@forge.test", "role": "student"}, format="json"
    )
    uid, token = link_params(res.data["invite_link"])
    assert (
        api_client.post(
            SET,
            {"uid": uid, "token": "bad-token", "new_password": "Chosen-Pass#2026"},
            format="json",
        ).status_code
        == 400
    )
    assert (
        api_client.post(
            SET, {"uid": "zzz", "token": token, "new_password": "Chosen-Pass#2026"}, format="json"
        ).status_code
        == 400
    )
    weak = api_client.post(SET, {"uid": uid, "token": token, "new_password": "123"}, format="json")
    assert weak.status_code == 400 and "new_password" in weak.data["errors"]


def test_admin_reset_returns_reset_link_and_blocks_old_password(
    auth_client, admin_user, student_user, password, api_client
):
    res = auth_client(admin_user).post(f"{API}/users/{student_user.pk}/reset-password/")
    assert res.status_code == 200 and "reset_link" in res.data and "temp_password" not in res.data
    student_user.refresh_from_db()
    assert not student_user.has_usable_password()
    login = api_client.post(
        f"{API}/auth/token/", {"email": student_user.email, "password": password}, format="json"
    )
    assert login.status_code == 401


def test_bulk_import_returns_invite_links(auth_client, admin_user):
    from django.core.files.uploadedfile import SimpleUploadedFile

    csv = SimpleUploadedFile(
        "u.csv", b"email,role\nnew1@forge.test,student\n", content_type="text/csv"
    )
    res = auth_client(admin_user).post(
        f"{API}/users/bulk-import/", {"file": csv}, format="multipart"
    )
    assert res.data["created"][0]["invite_link"].count("token=") == 1
    assert "temp_password" not in res.data["created"][0]


def test_forgot_password_sends_link_for_active_users_only(api_client, student_user):
    inactive = UserFactory(is_active=False, email="gone@forge.test")
    for email in (student_user.email, inactive.email, "nobody@forge.test"):
        assert api_client.post(FORGOT, {"email": email}, format="json").status_code == 204
    assert [m.to for m in mail.outbox] == [[student_user.email]]
    assert "/set-password?" in mail.outbox[0].body


def test_admin_can_still_set_explicit_password(auth_client, admin_user, api_client):
    res = auth_client(admin_user).post(
        f"{API}/users/",
        {"email": "direct@forge.test", "role": "student", "password": "Given-Pass#2026"},
        format="json",
    )
    assert res.status_code == 201 and res.data["invite_link"] is None
    login = api_client.post(
        f"{API}/auth/token/",
        {"email": "direct@forge.test", "password": "Given-Pass#2026"},
        format="json",
    )
    assert login.status_code == 200
