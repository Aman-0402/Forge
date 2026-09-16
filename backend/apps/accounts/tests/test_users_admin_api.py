import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import Department
from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.notifications.models import Notification

User = get_user_model()

URL = "/api/v1/users/"
TOKEN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"
ME = "/api/v1/auth/me/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(auth_client, admin_user):
    return auth_client(admin_user)


@pytest.fixture
def cse():
    return Department.objects.create(name="Computer Science", code="CSE")


def detail(user):
    return f"{URL}{user.pk}/"


# ---------- permissions ----------


def test_role_matrix(api_client, auth_client, admin_user, faculty_user, student_user):
    assert api_client.get(URL).status_code == 401
    assert auth_client(faculty_user).get(URL).status_code == 403
    assert auth_client(student_user).get(URL).status_code == 403
    assert auth_client(admin_user).get(URL).status_code == 200
    body = {"email": "x@forge.test", "role": "student"}
    assert auth_client(faculty_user).post(URL, body, format="json").status_code == 403


# ---------- list / filter ----------


def test_filter_by_role_department_active_and_search(admin, admin_user, cse):
    UserFactory(role="faculty", email="prof@forge.test", department=cse)
    s = UserFactory(role="student", email="stud@forge.test", first_name="Qwzyxal")
    s.student_profile.roll_number = "CSE-042"
    s.student_profile.save()
    UserFactory(role="student", email="gone@forge.test", is_active=False)

    def emails(params):
        return {u["email"] for u in admin.get(URL, params).data["results"]}

    assert emails({"role": "faculty"}) == {"prof@forge.test"}
    assert emails({"department": cse.pk}) == {"prof@forge.test"}
    assert "gone@forge.test" in emails({"is_active": "false"})
    assert emails({"search": "qwzyx"}) == {"stud@forge.test"}
    assert emails({"search": "CSE-042"}) == {"stud@forge.test"}


def test_list_includes_profile_and_department(admin, cse):
    UserFactory(role="faculty", department=cse)
    row = next(u for u in admin.get(URL, {"role": "faculty"}).data["results"])
    assert row["department"] == cse.pk
    assert row["department_detail"]["code"] == "CSE"
    assert "employee_id" in row["profile"]


# ---------- create ----------


def test_create_without_password_generates_temp_password(admin, api_client, cse):
    res = admin.post(
        URL,
        {
            "email": "new.fac@forge.test",
            "first_name": "New",
            "role": "faculty",
            "department": cse.pk,
            "profile": {"employee_id": "EMP-7", "designation": "Lecturer"},
        },
        format="json",
    )
    assert res.status_code == 201, res.data
    temp = res.data["temp_password"]
    assert temp and "password" not in res.data
    user = User.objects.get(email="new.fac@forge.test")
    assert user.role == "faculty" and user.department == cse and user.must_change_password
    assert user.faculty_profile.employee_id == "EMP-7"
    login = api_client.post(TOKEN, {"email": user.email, "password": temp}, format="json")
    assert login.status_code == 200
    assert Notification.objects.filter(recipient=user, kind="account").exists()
    assert mail.outbox and mail.outbox[0].to == [user.email]
    assert AuditLog.objects.filter(action="user.create", target_id=str(user.pk)).exists()


def test_create_with_password_does_not_force_change(admin):
    res = admin.post(
        URL,
        {"email": "s@forge.test", "role": "student", "password": "Given-Pass#2026"},
        format="json",
    )
    assert res.status_code == 201, res.data
    assert res.data["temp_password"] is None
    user = User.objects.get(email="s@forge.test")
    assert user.check_password("Given-Pass#2026") and not user.must_change_password


@pytest.mark.parametrize(
    "body",
    [
        {"email": "bad-role@forge.test", "role": "superuser"},
        {"email": "weak@forge.test", "role": "student", "password": "123"},
        {"role": "student"},
    ],
)
def test_create_validation_errors(admin, body):
    assert admin.post(URL, body, format="json").status_code == 400


def test_create_duplicate_email_rejected(admin, student_user):
    body = {"email": student_user.email, "role": "student"}
    assert admin.post(URL, body, format="json").status_code == 400


def test_create_admin_role_does_not_grant_django_superuser(admin):
    res = admin.post(URL, {"email": "a2@forge.test", "role": "admin"}, format="json")
    assert res.status_code == 201
    user = User.objects.get(email="a2@forge.test")
    assert user.role == "admin" and not user.is_superuser


# ---------- update ----------


def test_update_role_department_and_profile(admin, student_user, cse):
    res = admin.patch(
        detail(student_user),
        {"department": cse.pk, "profile": {"roll_number": "CSE-1", "batch": "2026", "year": 1}},
        format="json",
    )
    assert res.status_code == 200, res.data
    student_user.refresh_from_db()
    assert student_user.department == cse
    assert student_user.student_profile.roll_number == "CSE-1"
    log = AuditLog.objects.get(action="user.update", target_id=str(student_user.pk))
    assert "department" in log.metadata["fields"] and "profile" in log.metadata["fields"]


def test_duplicate_roll_number_rejected(admin, cse):
    a = UserFactory(role="student")
    a.student_profile.roll_number = "R1"
    a.student_profile.save()
    b = UserFactory(role="student")
    res = admin.patch(detail(b), {"profile": {"roll_number": "R1"}}, format="json")
    assert res.status_code == 400


def test_admin_cannot_demote_or_deactivate_self(admin, admin_user):
    assert admin.patch(detail(admin_user), {"role": "student"}, format="json").status_code == 400
    assert admin.patch(detail(admin_user), {"is_active": False}, format="json").status_code == 400
    assert admin.delete(detail(admin_user)).status_code == 400
    admin_user.refresh_from_db()
    assert admin_user.role == "admin" and admin_user.is_active


def test_admin_can_edit_own_name(admin, admin_user):
    assert admin.patch(detail(admin_user), {"first_name": "Boss"}, format="json").status_code == 200


# ---------- deactivate ----------


def test_delete_deactivates_and_revokes_tokens(admin, api_client, student_user, password):
    tokens = api_client.post(
        TOKEN, {"email": student_user.email, "password": password}, format="json"
    ).data
    res = admin.delete(detail(student_user))
    assert res.status_code == 204
    student_user.refresh_from_db()
    assert not student_user.is_active
    assert AuditLog.objects.filter(action="user.deactivate").exists()

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api_client.get(ME).status_code == 401
    api_client.credentials()
    assert (
        api_client.post(REFRESH, {"refresh": tokens["refresh"]}, format="json").status_code == 401
    )


def test_reactivate_via_patch(admin, student_user):
    student_user.is_active = False
    student_user.save()
    assert admin.patch(detail(student_user), {"is_active": True}, format="json").status_code == 200
    student_user.refresh_from_db()
    assert student_user.is_active


# ---------- reset password ----------


def test_reset_password(admin, api_client, student_user, password):
    old = api_client.post(TOKEN, {"email": student_user.email, "password": password}, format="json")
    res = admin.post(f"{detail(student_user)}reset-password/")
    assert res.status_code == 200
    temp = res.data["temp_password"]
    student_user.refresh_from_db()
    assert student_user.must_change_password
    assert not student_user.check_password(password)
    assert student_user.check_password(temp)
    refresh = api_client.post(REFRESH, {"refresh": old.data["refresh"]}, format="json")
    assert refresh.status_code == 401
    assert Notification.objects.filter(recipient=student_user, kind="account").exists()
    assert AuditLog.objects.filter(action="user.reset_password").exists()


def test_reset_password_admin_only(auth_client, faculty_user, student_user):
    url = f"{detail(student_user)}reset-password/"
    assert auth_client(faculty_user).post(url).status_code == 403


def test_change_password_clears_must_change_flag(admin, auth_client, student_user):
    temp = admin.post(f"{detail(student_user)}reset-password/").data["temp_password"]
    student_user.refresh_from_db()
    res = auth_client(student_user).post(
        "/api/v1/auth/change-password/",
        {"old_password": temp, "new_password": "Brand-New#Pass1"},
        format="json",
    )
    assert res.status_code == 200
    student_user.refresh_from_db()
    assert not student_user.must_change_password


# ---------- bulk import ----------


def csv_file(text, name="users.csv"):
    return SimpleUploadedFile(name, text.encode("utf-8"), content_type="text/csv")


def test_bulk_import_creates_valid_rows_and_reports_errors(admin, cse, student_user):
    text = (
        "email,first_name,last_name,role,department_code,roll_number\n"
        "a1@forge.test,Asha,K,student,CSE,CSE-100\n"
        "f1@forge.test,Farid,M,faculty,CSE,\n"
        "bad@forge.test,Bad,Role,wizard,CSE,\n"
        f"{student_user.email},Dup,Email,student,,\n"
        "nodept@forge.test,No,Dept,student,XYZ,\n"
        "dupe-roll@forge.test,Dup,Roll,student,CSE,CSE-100\n"
        ",Missing,Email,student,,\n"
    )
    res = admin.post(f"{URL}bulk-import/", {"file": csv_file(text)}, format="multipart")
    assert res.status_code == 200, res.data
    assert [c["email"] for c in res.data["created"]] == ["a1@forge.test", "f1@forge.test"]
    assert all(c["temp_password"] for c in res.data["created"])
    assert [e["row"] for e in res.data["errors"]] == [4, 5, 6, 7, 8]
    a1 = User.objects.get(email="a1@forge.test")
    assert a1.department == cse and a1.student_profile.roll_number == "CSE-100"
    assert a1.must_change_password
    assert not User.objects.filter(email="dupe-roll@forge.test").exists()
    log = AuditLog.objects.get(action="user.bulk_import")
    assert log.metadata == {"created": 2, "failed": 5}


def test_bulk_import_requires_file_and_headers(admin):
    assert admin.post(f"{URL}bulk-import/", {}, format="multipart").status_code == 400
    bad = csv_file("name,age\nx,1\n")
    assert admin.post(f"{URL}bulk-import/", {"file": bad}, format="multipart").status_code == 400


def test_bulk_import_admin_only(auth_client, faculty_user):
    res = auth_client(faculty_user).post(
        f"{URL}bulk-import/", {"file": csv_file("email,role\n")}, format="multipart"
    )
    assert res.status_code == 403
