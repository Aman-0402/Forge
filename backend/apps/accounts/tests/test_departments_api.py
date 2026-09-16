import pytest

from apps.accounts.models import Department
from apps.audit.models import AuditLog

URL = "/api/v1/departments/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def dept():
    return Department.objects.create(name="Computer Science", code="CSE")


def test_any_authenticated_user_can_list(api_client, auth_client, student_user, dept):
    assert api_client.get(URL).status_code == 401
    res = auth_client(student_user).get(URL)
    assert res.status_code == 200
    assert res.data["results"][0]["code"] == "CSE"


def test_only_admin_can_create(auth_client, admin_user, faculty_user, student_user):
    body = {"name": "Mechanical", "code": "MECH"}
    assert auth_client(faculty_user).post(URL, body, format="json").status_code == 403
    assert auth_client(student_user).post(URL, body, format="json").status_code == 403
    res = auth_client(admin_user).post(URL, body, format="json")
    assert res.status_code == 201
    assert AuditLog.objects.filter(action="department.create", target_id=str(res.data["id"]))


def test_admin_update_and_delete_are_audited(auth_client, admin_user, dept):
    client = auth_client(admin_user)
    assert client.patch(f"{URL}{dept.pk}/", {"name": "CS"}, format="json").status_code == 200
    assert client.delete(f"{URL}{dept.pk}/").status_code == 204
    actions = set(AuditLog.objects.values_list("action", flat=True))
    assert {"department.update", "department.delete"} <= actions


def test_faculty_cannot_update_or_delete(auth_client, faculty_user, dept):
    client = auth_client(faculty_user)
    assert client.patch(f"{URL}{dept.pk}/", {"name": "x"}, format="json").status_code == 403
    assert client.delete(f"{URL}{dept.pk}/").status_code == 403


def test_code_must_be_unique(auth_client, admin_user, dept):
    res = auth_client(admin_user).post(URL, {"name": "Other", "code": "CSE"}, format="json")
    assert res.status_code == 400


def test_list_includes_user_count(auth_client, admin_user, dept):
    from apps.accounts.tests.factories import UserFactory

    UserFactory(department=dept)
    UserFactory(department=dept)
    res = auth_client(admin_user).get(URL)
    assert res.data["results"][0]["user_count"] == 2
