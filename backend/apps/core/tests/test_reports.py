from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.coding.models import CodeSubmission
from apps.coding.tests.factories import LanguageFactory, ProblemFactory
from apps.courses.tests.factories import CourseFactory, EnrollmentFactory
from apps.exams.models import Attempt
from apps.exams.tests.factories import ExamFactory
from apps.notifications.models import ContactMessage

URL = "/api/v1/reports/overview/"

pytestmark = pytest.mark.django_db


def make_attempt(exam, student, **kw):
    defaults = dict(deadline_at=timezone.now() + timedelta(hours=1))
    defaults.update(kw)
    return Attempt.objects.create(exam=exam, student=student, **defaults)


def make_submission(problem, student, **kw):
    defaults = dict(language=LanguageFactory(), source_code="print(1)")
    defaults.update(kw)
    return CodeSubmission.objects.create(problem=problem, student=student, **defaults)


def test_admin_only(auth_client, faculty_user, student_user, api_client):
    assert api_client.get(URL).status_code in (401, 403)
    assert auth_client(faculty_user).get(URL).status_code == 403
    assert auth_client(student_user).get(URL).status_code == 403


def test_overview_shape_and_counts(auth_client, admin_user, faculty_user, student_user):
    UserFactory(role="student")
    UserFactory(role="student", is_active=False)

    course_a = CourseFactory(instructor=faculty_user, status="published")
    CourseFactory(instructor=faculty_user, status="draft")
    EnrollmentFactory(course=course_a, student=student_user, status="active")
    EnrollmentFactory(course=course_a, student=UserFactory(role="student"), status="active")
    EnrollmentFactory(course=course_a, student=UserFactory(role="student"), status="completed")

    exam = ExamFactory(course=course_a, created_by=faculty_user)
    make_attempt(exam, student_user, status="graded", passed=True)
    make_attempt(exam, UserFactory(role="student"), status="graded", passed=False)
    make_attempt(exam, UserFactory(role="student"), status="in_progress")

    problem = ProblemFactory(course=course_a, created_by=faculty_user)
    make_submission(problem, student_user, verdict=CodeSubmission.Verdict.ACCEPTED, status="done")
    make_submission(
        problem, student_user, verdict=CodeSubmission.Verdict.WRONG_ANSWER, status="done"
    )
    make_submission(problem, student_user, verdict=CodeSubmission.Verdict.ACCEPTED, status="done")

    ContactMessage.objects.create(name="A", email="a@b.com", message="hi")

    res = auth_client(admin_user).get(URL)
    assert res.status_code == 200, res.data
    data = res.data

    roles = {r["label"]: r["count"] for r in data["users_by_role"]}
    assert roles["student"] >= 4 and roles["admin"] >= 1 and roles["faculty"] >= 1
    assert data["users_active"]["inactive"] >= 1

    statuses = {c["label"]: c["count"] for c in data["courses_by_status"]}
    assert statuses["published"] >= 1 and statuses["draft"] >= 1

    enrollments = {e["label"]: e["count"] for e in data["enrollments_by_status"]}
    assert enrollments["active"] >= 1 and enrollments["completed"] >= 1

    assert data["exam_pass_fail"] == {"passed": 1, "failed": 1, "ungraded": 1}

    verdicts = {v["label"]: v["count"] for v in data["coding_submissions_by_verdict"]}
    assert verdicts["accepted"] == 2 and verdicts["wrong_answer"] == 1

    top_courses = data["top_courses_by_enrollment"]
    assert top_courses[0]["code"] == course_a.code
    assert top_courses[0]["count"] == 2

    assert data["contact_messages_total"] >= 1
    assert "generated_at" in data


def test_overview_handles_empty_platform(auth_client, admin_user):
    res = auth_client(admin_user).get(URL)
    assert res.status_code == 200
    assert data_or_empty(res.data, "top_courses_by_enrollment") == []
    assert data_or_empty(res.data, "coding_submissions_by_verdict") == []
    assert res.data["exam_pass_fail"] == {"passed": 0, "failed": 0, "ungraded": 0}


def data_or_empty(data, key):
    return data[key]
