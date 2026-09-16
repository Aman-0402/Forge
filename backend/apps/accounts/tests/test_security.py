import pytest

API = "/api/v1"
TOKEN = f"{API}/auth/token/"
REFRESH = f"{API}/auth/token/refresh/"
ME = f"{API}/auth/me/"
CHANGE = f"{API}/auth/change-password/"

pytestmark = pytest.mark.django_db


def login(client, email, password):
    return client.post(TOKEN, {"email": email, "password": password}, format="json")


def bearer(client, access):
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


# ---------- token invalidation ----------


def test_change_password_revokes_old_tokens_and_returns_new_ones(
    api_client, student_user, password
):
    old = login(api_client, student_user.email, password).data
    bearer(api_client, old["access"])
    res = api_client.post(
        CHANGE, {"old_password": password, "new_password": "Fresh-Pass#2026"}, format="json"
    )
    assert res.status_code == 200, res.data
    assert {"access", "refresh"} <= res.data.keys()

    stale = api_client.get(ME)
    assert stale.status_code == 401 and stale.data["code"] == "token_revoked"
    assert api_client.post(REFRESH, {"refresh": old["refresh"]}, format="json").status_code == 401

    bearer(api_client, res.data["access"])
    assert api_client.get(ME).status_code == 200


def test_admin_reset_revokes_access_tokens(
    api_client, auth_client, admin_user, student_user, password
):
    old = login(api_client, student_user.email, password).data
    auth_client(admin_user).post(f"{API}/users/{student_user.pk}/reset-password/")
    bearer(api_client, old["access"])
    assert api_client.get(ME).status_code == 401


# ---------- forced password change ----------


def test_must_change_password_blocks_other_endpoints(api_client, student_user, password):
    student_user.must_change_password = True
    student_user.save()
    tokens = login(api_client, student_user.email, password).data
    bearer(api_client, tokens["access"])

    blocked = api_client.get(f"{API}/courses/")
    assert blocked.status_code == 403 and blocked.data["code"] == "password_change_required"
    assert api_client.get(ME).status_code == 200

    res = api_client.post(
        CHANGE, {"old_password": password, "new_password": "Fresh-Pass#2026"}, format="json"
    )
    assert res.status_code == 200
    bearer(api_client, res.data["access"])
    assert api_client.get(f"{API}/courses/").status_code == 200


# ---------- login lockout ----------


def test_login_locks_after_repeated_failures(api_client, student_user, password):
    for _ in range(5):
        assert login(api_client, student_user.email, "wrong-password").status_code == 401
    locked = login(api_client, student_user.email, password)
    assert locked.status_code == 429 and locked.data["code"] == "login_locked"


def test_successful_login_resets_failure_count(api_client, student_user, password):
    for _ in range(4):
        login(api_client, student_user.email, "wrong-password")
    assert login(api_client, student_user.email, password).status_code == 200
    for _ in range(4):
        login(api_client, student_user.email, "wrong-password")
    assert login(api_client, student_user.email, password).status_code == 200


def test_lockout_is_case_insensitive_on_email(api_client, student_user, password):
    for _ in range(5):
        login(api_client, student_user.email.upper(), "wrong-password")
    assert login(api_client, student_user.email, password).status_code == 429
