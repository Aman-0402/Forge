import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
def test_create_user_uses_email_as_login_and_defaults_to_student():
    user = User.objects.create_user(email="A@Forge.Test", password="x-Secret-123")
    assert user.email == "A@forge.test"
    assert user.role == User.Role.STUDENT
    assert user.check_password("x-Secret-123")
    assert not user.is_staff
    assert User.USERNAME_FIELD == "email"


@pytest.mark.django_db
def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="x")


@pytest.mark.django_db
def test_create_superuser_is_admin_role_and_staff():
    user = User.objects.create_superuser(email="root@forge.test", password="x-Secret-123")
    assert user.role == User.Role.ADMIN
    assert user.is_staff and user.is_superuser


@pytest.mark.django_db
def test_email_is_unique():
    User.objects.create_user(email="dup@forge.test", password="x")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="dup@forge.test", password="x")


@pytest.mark.django_db
def test_role_helpers():
    user = User(role=User.Role.FACULTY)
    assert user.is_faculty and not user.is_admin_role and not user.is_student


@pytest.mark.django_db
def test_department_str_and_user_link():
    from apps.accounts.models import Department

    dept = Department.objects.create(name="Computer Science", code="CSE")
    user = User.objects.create_user(email="d@forge.test", password="x", department=dept)
    assert str(dept) == "CSE - Computer Science"
    assert user.department == dept
