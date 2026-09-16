import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

REGISTER = "/api/v1/auth/register/"
TOKEN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"
LOGOUT = "/api/v1/auth/logout/"
ME = "/api/v1/auth/me/"
CHANGE_PASSWORD = "/api/v1/auth/change-password/"

pytestmark = pytest.mark.django_db


def test_register_creates_student(api_client, password):
    res = api_client.post(
        REGISTER,
        {"email": "new@forge.test", "password": password, "first_name": "N", "last_name": "S"},
        format="json",
    )
    assert res.status_code == 201, res.data
    assert res.data["role"] == "student"
    assert "password" not in res.data
    assert User.objects.get(email="new@forge.test").role == "student"


def test_register_ignores_role_escalation(api_client, password):
    res = api_client.post(
        REGISTER, {"email": "evil@forge.test", "password": password, "role": "admin"}, format="json"
    )
    assert res.status_code == 201
    assert User.objects.get(email="evil@forge.test").role == "student"


def test_register_rejects_weak_password(api_client):
    res = api_client.post(REGISTER, {"email": "w@forge.test", "password": "123"}, format="json")
    assert res.status_code == 400
    assert "password" in res.data["errors"]


def test_register_rejects_duplicate_email(api_client, student_user, password):
    res = api_client.post(
        REGISTER, {"email": student_user.email, "password": password}, format="json"
    )
    assert res.status_code == 400


def test_token_obtain_and_refresh(api_client, student_user, password):
    res = api_client.post(TOKEN, {"email": student_user.email, "password": password}, format="json")
    assert res.status_code == 200, res.data
    assert {"access", "refresh"} <= res.data.keys()
    res2 = api_client.post(REFRESH, {"refresh": res.data["refresh"]}, format="json")
    assert res2.status_code == 200
    assert "access" in res2.data


def test_token_rejects_bad_password(api_client, student_user):
    res = api_client.post(TOKEN, {"email": student_user.email, "password": "nope"}, format="json")
    assert res.status_code == 401


def test_inactive_user_cannot_login(api_client, student_user, password):
    student_user.is_active = False
    student_user.save()
    res = api_client.post(TOKEN, {"email": student_user.email, "password": password}, format="json")
    assert res.status_code == 401


def test_me_requires_auth(api_client):
    res = api_client.get(ME)
    assert res.status_code == 401
    assert "detail" in res.data


def test_me_returns_current_user_with_bearer_token(api_client, faculty_user, password):
    tokens = api_client.post(
        TOKEN, {"email": faculty_user.email, "password": password}, format="json"
    ).data
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    res = api_client.get(ME)
    assert res.status_code == 200
    assert res.data["email"] == faculty_user.email
    assert res.data["role"] == "faculty"


def test_me_patch_updates_names_but_not_role_or_email(auth_client, student_user):
    client = auth_client(student_user)
    res = client.patch(
        ME, {"first_name": "Changed", "role": "admin", "email": "x@forge.test"}, format="json"
    )
    assert res.status_code == 200
    student_user.refresh_from_db()
    assert student_user.first_name == "Changed"
    assert student_user.role == "student"
    assert student_user.email == "student@forge.test"


def test_change_password_requires_correct_old_password(auth_client, student_user):
    res = auth_client(student_user).post(
        CHANGE_PASSWORD, {"old_password": "wrong", "new_password": "An0ther-Str0ng!"}, format="json"
    )
    assert res.status_code == 400


def test_change_password_success(auth_client, student_user, password):
    res = auth_client(student_user).post(
        CHANGE_PASSWORD,
        {"old_password": password, "new_password": "An0ther-Str0ng!"},
        format="json",
    )
    assert res.status_code == 204
    student_user.refresh_from_db()
    assert student_user.check_password("An0ther-Str0ng!")


def test_logout_blacklists_refresh_token(api_client, student_user, password):
    tokens = api_client.post(
        TOKEN, {"email": student_user.email, "password": password}, format="json"
    ).data
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    res = api_client.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json")
    assert res.status_code == 205
    res2 = api_client.post(REFRESH, {"refresh": tokens["refresh"]}, format="json")
    assert res2.status_code == 401


def test_error_envelope_on_validation_error(api_client):
    res = api_client.post(REGISTER, {}, format="json")
    assert res.status_code == 400
    assert res.data["code"] == "validation_error"
    assert "email" in res.data["errors"]
