from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Department
from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.notifications.models import Announcement, Notification

URL = "/api/v1/announcements/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def cse():
    return Department.objects.create(name="Computer Science", code="CSE")


@pytest.fixture
def ece():
    return Department.objects.create(name="Electronics", code="ECE")


def make(author, audience="all", department=None, **kw):
    return Announcement.objects.create(
        author=author,
        title=kw.pop("title", audience),
        body="b",
        audience=audience,
        department=department,
        **kw,
    )


def titles(client, params=None):
    return {a["title"] for a in client.get(URL, params or {}).data["results"]}


# ---------- create ----------


def test_admin_posts_to_all_and_everyone_active_is_notified(auth_client, admin_user):
    s = UserFactory(role="student")
    f = UserFactory(role="faculty")
    UserFactory(role="student", is_active=False)
    res = auth_client(admin_user).post(
        URL, {"title": "Holiday", "body": "Closed Monday", "audience": "all"}, format="json"
    )
    assert res.status_code == 201, res.data
    assert res.data["author_name"]
    notified = set(
        Notification.objects.filter(kind="announcement").values_list("recipient_id", flat=True)
    )
    assert notified == {s.pk, f.pk}
    assert AuditLog.objects.filter(action="announcement.create").exists()


def test_admin_posts_to_students_only_notifies_students(auth_client, admin_user):
    s = UserFactory(role="student")
    UserFactory(role="faculty")
    auth_client(admin_user).post(
        URL, {"title": "Exams", "body": "x", "audience": "students"}, format="json"
    )
    notified = list(Notification.objects.values_list("recipient_id", flat=True))
    assert notified == [s.pk]


def test_future_announcement_does_not_notify_yet(auth_client, admin_user):
    UserFactory(role="student")
    future = (timezone.now() + timedelta(days=2)).isoformat()
    res = auth_client(admin_user).post(
        URL,
        {"title": "Later", "body": "x", "audience": "all", "published_at": future},
        format="json",
    )
    assert res.status_code == 201
    assert not Notification.objects.exists()


def test_department_audience_requires_department(auth_client, admin_user):
    res = auth_client(admin_user).post(
        URL, {"title": "t", "body": "b", "audience": "department"}, format="json"
    )
    assert res.status_code == 400
    assert "department" in res.data["errors"]


def test_department_is_cleared_for_non_department_audience(auth_client, admin_user, cse):
    res = auth_client(admin_user).post(
        URL, {"title": "t", "body": "b", "audience": "all", "department": cse.pk}, format="json"
    )
    assert res.status_code == 201
    assert res.data["department"] is None


def test_expiry_must_be_after_publish(auth_client, admin_user):
    now = timezone.now()
    res = auth_client(admin_user).post(
        URL,
        {
            "title": "t",
            "body": "b",
            "audience": "all",
            "published_at": now.isoformat(),
            "expires_at": (now - timedelta(hours=1)).isoformat(),
        },
        format="json",
    )
    assert res.status_code == 400


def test_student_cannot_post(auth_client, student_user):
    body = {"title": "t", "body": "b", "audience": "all"}
    assert auth_client(student_user).post(URL, body, format="json").status_code == 403


def test_faculty_can_post_only_to_own_department(auth_client, cse, ece):
    fac = UserFactory(role="faculty", department=cse)
    peer = UserFactory(role="student", department=cse)
    UserFactory(role="student", department=ece)
    client = auth_client(fac)

    for audience in ("all", "students", "faculty"):
        body = {"title": "t", "body": "b", "audience": audience}
        assert client.post(URL, body, format="json").status_code == 400

    other = {"title": "t", "body": "b", "audience": "department", "department": ece.pk}
    assert client.post(URL, other, format="json").status_code == 400

    own = {"title": "CSE lab", "body": "b", "audience": "department", "department": cse.pk}
    assert client.post(URL, own, format="json").status_code == 201
    assert list(Notification.objects.values_list("recipient_id", flat=True)) == [peer.pk]


def test_faculty_without_department_cannot_post(auth_client, faculty_user, cse):
    body = {"title": "t", "body": "b", "audience": "department", "department": cse.pk}
    assert auth_client(faculty_user).post(URL, body, format="json").status_code == 400


# ---------- visibility ----------


def test_visibility_by_role_department_and_time(auth_client, admin_user, cse, ece):
    now = timezone.now()
    make(admin_user, "all", title="all")
    make(admin_user, "students", title="students")
    make(admin_user, "faculty", title="faculty")
    make(admin_user, "department", cse, title="cse")
    make(admin_user, "department", ece, title="ece")
    make(admin_user, "all", title="future", published_at=now + timedelta(days=1))
    make(admin_user, "all", title="expired", expires_at=now - timedelta(minutes=1))

    student = UserFactory(role="student", department=cse)
    faculty = UserFactory(role="faculty", department=ece)

    assert titles(auth_client(student)) == {"all", "students", "cse"}
    assert titles(auth_client(faculty)) == {"all", "faculty", "ece"}
    assert titles(auth_client(admin_user)) == {
        "all",
        "students",
        "faculty",
        "cse",
        "ece",
        "future",
        "expired",
    }


def test_list_requires_auth(api_client):
    assert api_client.get(URL).status_code == 401


# ---------- update / delete ----------


def test_author_faculty_can_edit_and_delete_own(auth_client, cse):
    fac = UserFactory(role="faculty", department=cse)
    ann = make(fac, "department", cse)
    client = auth_client(fac)
    assert client.patch(f"{URL}{ann.pk}/", {"title": "new"}, format="json").status_code == 200
    assert client.delete(f"{URL}{ann.pk}/").status_code == 204
    actions = set(AuditLog.objects.values_list("action", flat=True))
    assert {"announcement.update", "announcement.delete"} <= actions


def test_other_faculty_cannot_edit(auth_client, cse):
    author = UserFactory(role="faculty", department=cse)
    other = UserFactory(role="faculty", department=cse)
    ann = make(author, "department", cse)
    res = auth_client(other).patch(f"{URL}{ann.pk}/", {"title": "x"}, format="json")
    assert res.status_code == 403


def test_faculty_cannot_widen_audience_on_edit(auth_client, cse):
    fac = UserFactory(role="faculty", department=cse)
    ann = make(fac, "department", cse)
    res = auth_client(fac).patch(f"{URL}{ann.pk}/", {"audience": "all"}, format="json")
    assert res.status_code == 400


def test_admin_can_edit_any(auth_client, admin_user, cse):
    fac = UserFactory(role="faculty", department=cse)
    ann = make(fac, "department", cse)
    res = auth_client(admin_user).patch(f"{URL}{ann.pk}/", {"title": "fixed"}, format="json")
    assert res.status_code == 200


# ---------- course audience ----------


def test_faculty_posts_to_managed_course_and_enrolled_are_notified(auth_client):
    from apps.courses.tests.factories import CourseFactory, EnrollmentFactory

    fac = UserFactory(role="faculty")
    co = UserFactory(role="faculty")
    course = CourseFactory(instructor=fac)
    course.co_instructors.add(co)
    student = UserFactory(role="student")
    EnrollmentFactory(course=course, student=student)
    dropped = UserFactory(role="student")
    EnrollmentFactory(course=course, student=dropped, status="dropped")
    UserFactory(role="student")

    res = auth_client(fac).post(
        URL,
        {"title": "Quiz Friday", "body": "Chapter 2", "audience": "course", "course": course.pk},
        format="json",
    )
    assert res.status_code == 201, res.data
    assert res.data["course_title"] == course.title
    notified = set(Notification.objects.values_list("recipient_id", flat=True))
    assert notified == {student.pk, co.pk}


def test_faculty_cannot_post_to_unmanaged_course(auth_client):
    from apps.courses.tests.factories import CourseFactory

    fac = UserFactory(role="faculty")
    course = CourseFactory()
    body = {"title": "t", "body": "b", "audience": "course", "course": course.pk}
    assert auth_client(fac).post(URL, body, format="json").status_code == 400


def test_course_audience_requires_course(auth_client, admin_user):
    body = {"title": "t", "body": "b", "audience": "course"}
    res = auth_client(admin_user).post(URL, body, format="json")
    assert res.status_code == 400 and "course" in res.data["errors"]


def test_course_announcement_visibility(auth_client, admin_user):
    from apps.courses.tests.factories import CourseFactory, EnrollmentFactory

    fac = UserFactory(role="faculty")
    course = CourseFactory(instructor=fac)
    make_course = Announcement.objects.create(
        author=admin_user, title="course-post", body="b", audience="course", course=course
    )
    enrolled = UserFactory(role="student")
    EnrollmentFactory(course=course, student=enrolled)
    outsider = UserFactory(role="student")
    other_fac = UserFactory(role="faculty")

    assert "course-post" in titles(auth_client(enrolled))
    assert "course-post" in titles(auth_client(fac))
    assert "course-post" not in titles(auth_client(outsider))
    assert "course-post" not in titles(auth_client(other_fac))
    assert auth_client(enrolled).get(URL, {"course": course.pk}).data["results"][0]["id"] == (
        make_course.pk
    )
