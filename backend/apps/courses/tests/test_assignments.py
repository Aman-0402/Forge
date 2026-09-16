from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.courses.models import AssignmentSubmission
from apps.courses.tests.factories import AssignmentFactory, CourseFactory, EnrollmentFactory
from apps.notifications.models import Notification

API = "/api/v1"

pytestmark = pytest.mark.django_db


@pytest.fixture
def course(faculty_user):
    return CourseFactory(instructor=faculty_user)


@pytest.fixture
def enrolled(course, student_user):
    EnrollmentFactory(course=course, student=student_user)
    return student_user


def upload(name="answer.pdf", size=50):
    return SimpleUploadedFile(name, b"%PDF" + b"x" * size)


def submit(client, assignment, data, fmt="multipart"):
    return client.post(f"{API}/assignments/{assignment.pk}/submit/", data, format=fmt)


# ---------- create / list ----------


def test_manager_creates_assignment_and_students_are_notified(
    auth_client, faculty_user, course, enrolled
):
    due = (timezone.now() + timedelta(days=3)).isoformat()
    res = auth_client(faculty_user).post(
        f"{API}/courses/{course.pk}/assignments/",
        {
            "title": "Essay",
            "description": "500 words",
            "max_marks": "20",
            "due_at": due,
            "attachment": upload("brief.pdf"),
        },
        format="multipart",
    )
    assert res.status_code == 201, res.data
    assert res.data["attachment"].endswith(".pdf")
    assert Notification.objects.filter(recipient=enrolled, kind="assignment").exists()
    assert AuditLog.objects.filter(action="assignment.create").exists()


def test_non_managers_cannot_create(auth_client, course, enrolled):
    url = f"{API}/courses/{course.pk}/assignments/"
    body = {"title": "x", "max_marks": "5"}
    assert auth_client(enrolled).post(url, body, format="json").status_code == 403
    other = UserFactory(role="faculty")
    assert auth_client(other).post(url, body, format="json").status_code == 403


def test_attachment_type_validated(auth_client, faculty_user, course):
    res = auth_client(faculty_user).post(
        f"{API}/courses/{course.pk}/assignments/",
        {"title": "x", "max_marks": "5", "attachment": SimpleUploadedFile("run.exe", b"MZ")},
        format="multipart",
    )
    assert res.status_code == 400


def test_list_access(auth_client, course, enrolled, faculty_user):
    AssignmentFactory(course=course, title="A1")
    url = f"{API}/courses/{course.pk}/assignments/"
    assert [a["title"] for a in auth_client(enrolled).get(url).data] == ["A1"]
    assert auth_client(faculty_user).get(url).status_code == 200
    stranger = UserFactory(role="student")
    assert auth_client(stranger).get(url).status_code == 403
    assert (
        auth_client(stranger).get(f"{API}/assignments/{course.assignments.first().pk}/").status_code
        == 403
    )


def test_student_list_shows_my_submission_and_manager_sees_counts(
    auth_client, faculty_user, course, enrolled
):
    a = AssignmentFactory(course=course)
    submit(auth_client(enrolled), a, {"text": "done"})
    mine = auth_client(enrolled).get(f"{API}/courses/{course.pk}/assignments/").data[0]
    assert mine["my_submission"]["graded"] is False
    row = auth_client(faculty_user).get(f"{API}/courses/{course.pk}/assignments/").data[0]
    assert (row["submission_count"], row["graded_count"]) == (1, 0)


# ---------- submit ----------


def test_student_submits_file(auth_client, course, enrolled):
    a = AssignmentFactory(course=course, due_at=timezone.now() + timedelta(days=1))
    res = submit(auth_client(enrolled), a, {"file": upload()})
    assert res.status_code == 201, res.data
    assert res.data["is_late"] is False
    assert AuditLog.objects.filter(action="assignment.submit").exists()


def test_submission_needs_file_or_text(auth_client, course, enrolled):
    a = AssignmentFactory(course=course)
    assert submit(auth_client(enrolled), a, {}).status_code == 400


def test_resubmit_replaces_until_graded(auth_client, faculty_user, course, enrolled):
    a = AssignmentFactory(course=course)
    client = auth_client(enrolled)
    first = submit(client, a, {"text": "v1"})
    second = submit(client, a, {"text": "v2"})
    assert (first.status_code, second.status_code) == (201, 200)
    assert AssignmentSubmission.objects.get().text == "v2"
    sub = AssignmentSubmission.objects.get()
    auth_client(faculty_user).post(
        f"{API}/submissions/{sub.pk}/grade/", {"marks": "8"}, format="json"
    )
    assert submit(client, a, {"text": "v3"}).status_code == 400


def test_late_submission_rules(auth_client, course, enrolled):
    past = timezone.now() - timedelta(hours=1)
    closed = AssignmentFactory(course=course, due_at=past, allow_late=False)
    lenient = AssignmentFactory(course=course, due_at=past, allow_late=True)
    client = auth_client(enrolled)
    assert submit(client, closed, {"text": "late"}).status_code == 400
    res = submit(client, lenient, {"text": "late"})
    assert res.status_code == 201 and res.data["is_late"] is True


def test_unenrolled_and_faculty_cannot_submit(auth_client, faculty_user, course):
    a = AssignmentFactory(course=course)
    stranger = UserFactory(role="student")
    assert submit(auth_client(stranger), a, {"text": "x"}).status_code == 403
    assert submit(auth_client(faculty_user), a, {"text": "x"}).status_code == 403


def test_submission_file_type_validated(auth_client, course, enrolled):
    a = AssignmentFactory(course=course)
    res = submit(auth_client(enrolled), a, {"file": SimpleUploadedFile("x.exe", b"MZ")})
    assert res.status_code == 400


# ---------- review / grade ----------


def test_submission_listing_by_role(auth_client, faculty_user, course, enrolled):
    a = AssignmentFactory(course=course)
    other = UserFactory(role="student")
    EnrollmentFactory(course=course, student=other)
    submit(auth_client(enrolled), a, {"text": "mine"})
    submit(auth_client(other), a, {"text": "theirs"})
    url = f"{API}/assignments/{a.pk}/submissions/"
    assert len(auth_client(faculty_user).get(url).data["results"]) == 2
    own = auth_client(enrolled).get(url).data["results"]
    assert [s["text"] for s in own] == ["mine"]


def test_submission_detail_access(auth_client, faculty_user, course, enrolled):
    a = AssignmentFactory(course=course)
    sub_id = submit(auth_client(enrolled), a, {"text": "mine"}).data["id"]
    other = UserFactory(role="student")
    EnrollmentFactory(course=course, student=other)
    assert auth_client(enrolled).get(f"{API}/submissions/{sub_id}/").status_code == 200
    assert auth_client(faculty_user).get(f"{API}/submissions/{sub_id}/").status_code == 200
    assert auth_client(other).get(f"{API}/submissions/{sub_id}/").status_code == 403


def test_grade_submission(auth_client, faculty_user, course, enrolled):
    a = AssignmentFactory(course=course, max_marks=10)
    sub_id = submit(auth_client(enrolled), a, {"text": "mine"}).data["id"]
    url = f"{API}/submissions/{sub_id}/grade/"
    manager = auth_client(faculty_user)
    assert manager.post(url, {"marks": "11"}, format="json").status_code == 400
    assert manager.post(url, {"marks": "-1"}, format="json").status_code == 400
    res = manager.post(url, {"marks": "9.5", "feedback": "Good"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["marks"] == "9.50" and res.data["graded_by"] == faculty_user.pk
    assert Notification.objects.filter(
        recipient=enrolled, kind="assignment", title__startswith="Graded"
    ).exists()
    assert AuditLog.objects.filter(action="assignment.grade").exists()
    assert auth_client(enrolled).post(url, {"marks": "10"}, format="json").status_code == 403


def test_filter_submissions_by_graded(auth_client, faculty_user, course, enrolled):
    a = AssignmentFactory(course=course)
    sub_id = submit(auth_client(enrolled), a, {"text": "x"}).data["id"]
    other = UserFactory(role="student")
    EnrollmentFactory(course=course, student=other)
    submit(auth_client(other), a, {"text": "y"})
    manager = auth_client(faculty_user)
    manager.post(f"{API}/submissions/{sub_id}/grade/", {"marks": "5"}, format="json")
    url = f"{API}/assignments/{a.pk}/submissions/"
    assert len(manager.get(url, {"graded": "true"}).data["results"]) == 1
    assert len(manager.get(url, {"graded": "false"}).data["results"]) == 1


def test_manager_updates_and_deletes_assignment(auth_client, faculty_user, course):
    a = AssignmentFactory(course=course)
    manager = auth_client(faculty_user)
    assert (
        manager.patch(f"{API}/assignments/{a.pk}/", {"title": "Renamed"}, format="json").status_code
        == 200
    )
    assert manager.delete(f"{API}/assignments/{a.pk}/").status_code == 204
