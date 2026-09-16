import pytest

from apps.accounts.models import FacultyProfile, StudentProfile
from apps.accounts.tests.factories import UserFactory

ME = "/api/v1/auth/me/"

pytestmark = pytest.mark.django_db


def test_student_gets_student_profile_only():
    user = UserFactory(role="student")
    assert StudentProfile.objects.filter(user=user).exists()
    assert not FacultyProfile.objects.filter(user=user).exists()


def test_faculty_gets_faculty_profile_only():
    user = UserFactory(role="faculty")
    assert FacultyProfile.objects.filter(user=user).exists()
    assert not StudentProfile.objects.filter(user=user).exists()


def test_admin_gets_no_profile():
    user = UserFactory(role="admin")
    assert not StudentProfile.objects.filter(user=user).exists()
    assert not FacultyProfile.objects.filter(user=user).exists()


def test_role_change_creates_matching_profile():
    user = UserFactory(role="student")
    user.role = "faculty"
    user.save()
    assert FacultyProfile.objects.filter(user=user).exists()


def test_blank_roll_numbers_do_not_collide():
    a = UserFactory(role="student")
    b = UserFactory(role="student")
    a.student_profile.roll_number = ""
    a.student_profile.save()
    b.student_profile.roll_number = ""
    b.student_profile.save()
    assert a.student_profile.roll_number is None


def test_me_includes_student_profile(auth_client, student_user):
    profile = student_user.student_profile
    profile.roll_number = "CSE-001"
    profile.batch = "2026"
    profile.save()
    res = auth_client(student_user).get(ME)
    assert res.data["profile"]["roll_number"] == "CSE-001"
    assert res.data["profile"]["batch"] == "2026"


def test_me_includes_faculty_profile(auth_client, faculty_user):
    res = auth_client(faculty_user).get(ME)
    assert set(res.data["profile"]) >= {"employee_id", "designation", "bio"}


def test_me_admin_profile_is_null(auth_client, admin_user):
    assert auth_client(admin_user).get(ME).data["profile"] is None


def test_me_student_can_edit_bio_but_not_roll_number(auth_client, student_user):
    res = auth_client(student_user).patch(
        ME, {"profile": {"bio": "hello", "roll_number": "HACK"}}, format="json"
    )
    assert res.status_code == 200, res.data
    student_user.student_profile.refresh_from_db()
    assert student_user.student_profile.bio == "hello"
    assert student_user.student_profile.roll_number is None
