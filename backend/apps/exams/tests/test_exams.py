from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.courses.tests.factories import CourseFactory, EnrollmentFactory
from apps.exams.models import Attempt, Exam, ExamQuestion
from apps.exams.tests.factories import (
    ExamFactory,
    QuestionBankFactory,
    add_questions,
    mcq,
    subjective,
)
from apps.notifications.models import Notification

API = "/api/v1"

pytestmark = pytest.mark.django_db


def iso(delta_minutes):
    return (timezone.now() + timedelta(minutes=delta_minutes)).isoformat()


def exam_body(**overrides):
    body = {
        "title": "Midterm",
        "starts_at": iso(60),
        "ends_at": iso(180),
        "duration_minutes": 45,
        "pass_marks": "4",
    }
    body.update(overrides)
    return body


# ---------- create / visibility ----------


def test_faculty_creates_draft_exam(auth_client, faculty_user):
    res = auth_client(faculty_user).post(f"{API}/exams/", exam_body(), format="json")
    assert res.status_code == 201, res.data
    assert res.data["status"] == "draft" and res.data["created_by"] == faculty_user.pk
    assert res.data["total_marks"] == "0.00"
    assert AuditLog.objects.filter(action="exam.create").exists()


def test_student_cannot_create(auth_client, student_user):
    assert (
        auth_client(student_user).post(f"{API}/exams/", exam_body(), format="json").status_code
        == 403
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"ends_at": iso(30), "starts_at": iso(60)},
        {"duration_minutes": 0},
    ],
)
def test_create_validation(auth_client, faculty_user, overrides):
    res = auth_client(faculty_user).post(f"{API}/exams/", exam_body(**overrides), format="json")
    assert res.status_code == 400


def test_course_exam_requires_managing_course(auth_client, faculty_user):
    mine = CourseFactory(instructor=faculty_user)
    other = CourseFactory()
    client = auth_client(faculty_user)
    assert (
        client.post(f"{API}/exams/", exam_body(course=other.pk), format="json").status_code == 400
    )
    assert client.post(f"{API}/exams/", exam_body(course=mine.pk), format="json").status_code == 201


def test_course_instructor_manages_exam_created_by_admin(auth_client, admin_user, faculty_user):
    course = CourseFactory(instructor=faculty_user)
    exam = ExamFactory(created_by=admin_user, course=course, status="draft")
    res = auth_client(faculty_user).patch(
        f"{API}/exams/{exam.pk}/", {"title": "Renamed"}, format="json"
    )
    assert res.status_code == 200


def test_staff_list_shows_managed_exams(auth_client, faculty_user):
    ExamFactory(created_by=faculty_user, title="mine", status="draft")
    ExamFactory(title="someone else")
    titles = {e["title"] for e in auth_client(faculty_user).get(f"{API}/exams/").data["results"]}
    assert titles == {"mine"}


def test_student_sees_only_eligible_non_draft_exams(auth_client, student_user):
    course = CourseFactory()
    EnrollmentFactory(course=course, student=student_user)
    ExamFactory(title="course exam", course=course)
    ExamFactory(title="other course", course=CourseFactory())
    ExamFactory(title="open to all")
    ExamFactory(title="draft", status="draft")
    invited = ExamFactory(title="invited", course=CourseFactory())
    invited.allowed_students.add(student_user)
    restricted = ExamFactory(title="restricted")
    restricted.allowed_students.add(UserFactory(role="student"))

    rows = auth_client(student_user).get(f"{API}/exams/").data["results"]
    assert {e["title"] for e in rows} == {"course exam", "open to all", "invited"}
    row = next(e for e in rows if e["title"] == "course exam")
    assert row["phase"] == "live"
    assert row["my_attempts"] == {"used": 0, "max": 1, "in_progress_id": None, "can_start": True}
    assert "attempt_count" not in row or row["attempt_count"] is None


# ---------- questions ----------


def test_add_questions_by_id_and_random_pick(auth_client, faculty_user):
    bank = QuestionBankFactory(owner=faculty_user)
    q1, q2 = mcq(bank=bank, marks=2), subjective(bank=bank, marks=5)
    for _ in range(5):
        mcq(bank=bank, difficulty="hard", marks=1)
    exam = ExamFactory(created_by=faculty_user, status="draft")
    client = auth_client(faculty_user)
    url = f"{API}/exams/{exam.pk}/questions/"

    res = client.post(url, {"question_ids": [q1.pk, q2.pk]}, format="json")
    assert res.status_code == 201, res.data
    res = client.post(url, {"bank": bank.pk, "count": 3, "difficulty": "hard"}, format="json")
    assert res.status_code == 201, res.data
    assert exam.exam_questions.count() == 5

    detail = client.get(f"{API}/exams/{exam.pk}/").data
    assert detail["question_count"] == 5 and detail["total_marks"] == "10.00"

    too_many = client.post(url, {"bank": bank.pk, "count": 10, "difficulty": "hard"}, format="json")
    assert too_many.status_code == 400
    dupe = client.post(url, {"question_ids": [q1.pk]}, format="json")
    assert dupe.status_code == 400


def test_cannot_add_questions_from_private_bank_of_someone_else(auth_client, faculty_user):
    foreign = mcq(bank=QuestionBankFactory())
    exam = ExamFactory(created_by=faculty_user, status="draft")
    res = auth_client(faculty_user).post(
        f"{API}/exams/{exam.pk}/questions/", {"question_ids": [foreign.pk]}, format="json"
    )
    assert res.status_code == 400


def test_marks_override_and_remove_question(auth_client, faculty_user):
    exam = add_questions(
        ExamFactory(created_by=faculty_user, status="draft"), mcq(marks=2), mcq(marks=2)
    )
    eq = exam.exam_questions.first()
    client = auth_client(faculty_user)
    res = client.patch(
        f"{API}/exams/{exam.pk}/questions/{eq.pk}/", {"marks_override": "3"}, format="json"
    )
    assert res.status_code == 200
    assert client.get(f"{API}/exams/{exam.pk}/").data["total_marks"] == "5.00"
    assert client.delete(f"{API}/exams/{exam.pk}/questions/{eq.pk}/").status_code == 204
    assert exam.exam_questions.count() == 1


def test_staff_question_list_includes_answers(auth_client, faculty_user):
    exam = add_questions(ExamFactory(created_by=faculty_user, status="draft"), mcq())
    rows = auth_client(faculty_user).get(f"{API}/exams/{exam.pk}/questions/").data
    assert "is_correct" in rows[0]["question"]["options"][0]


def test_edits_locked_after_attempts(auth_client, faculty_user, student_user):
    exam = add_questions(ExamFactory(created_by=faculty_user), mcq())
    Attempt.objects.create(exam=exam, student=student_user, deadline_at=exam.ends_at)
    client = auth_client(faculty_user)
    assert (
        client.patch(f"{API}/exams/{exam.pk}/", {"duration_minutes": 90}, format="json").status_code
        == 400
    )
    assert (
        client.patch(f"{API}/exams/{exam.pk}/", {"title": "Fixed typo"}, format="json").status_code
        == 200
    )
    add = client.post(
        f"{API}/exams/{exam.pk}/questions/", {"question_ids": [mcq().pk]}, format="json"
    )
    assert add.status_code == 400
    assert client.delete(f"{API}/exams/{exam.pk}/").status_code == 400


# ---------- lifecycle ----------


def test_schedule_requires_questions_and_future_end(auth_client, faculty_user):
    client = auth_client(faculty_user)
    empty = ExamFactory(created_by=faculty_user, status="draft")
    assert client.post(f"{API}/exams/{empty.pk}/schedule/").status_code == 400
    past = add_questions(
        ExamFactory(
            created_by=faculty_user,
            status="draft",
            starts_at=timezone.now() - timedelta(days=2),
            ends_at=timezone.now() - timedelta(days=1),
        ),
        mcq(),
    )
    assert client.post(f"{API}/exams/{past.pk}/schedule/").status_code == 400


def test_schedule_notifies_eligible_students(auth_client, faculty_user):
    course = CourseFactory(instructor=faculty_user)
    enrolled = UserFactory(role="student")
    EnrollmentFactory(course=course, student=enrolled)
    UserFactory(role="student")
    exam = add_questions(ExamFactory(created_by=faculty_user, course=course, status="draft"), mcq())
    res = auth_client(faculty_user).post(f"{API}/exams/{exam.pk}/schedule/")
    assert res.status_code == 200 and res.data["status"] == "scheduled"
    assert list(
        Notification.objects.filter(kind="exam").values_list("recipient_id", flat=True)
    ) == [enrolled.pk]
    assert AuditLog.objects.filter(action="exam.schedule").exists()


def test_unschedule_only_without_attempts(auth_client, faculty_user, student_user):
    exam = add_questions(ExamFactory(created_by=faculty_user), mcq())
    client = auth_client(faculty_user)
    assert client.post(f"{API}/exams/{exam.pk}/unschedule/").data["status"] == "draft"
    exam.status = Exam.Status.SCHEDULED
    exam.save()
    Attempt.objects.create(exam=exam, student=student_user, deadline_at=exam.ends_at)
    assert client.post(f"{API}/exams/{exam.pk}/unschedule/").status_code == 400


def test_extend_window(auth_client, faculty_user):
    exam = add_questions(ExamFactory(created_by=faculty_user), mcq())
    client = auth_client(faculty_user)
    earlier = (exam.ends_at - timedelta(minutes=5)).isoformat()
    assert (
        client.post(
            f"{API}/exams/{exam.pk}/extend/", {"ends_at": earlier}, format="json"
        ).status_code
        == 400
    )
    later = (exam.ends_at + timedelta(hours=1)).isoformat()
    res = client.post(f"{API}/exams/{exam.pk}/extend/", {"ends_at": later}, format="json")
    assert res.status_code == 200


def test_non_manager_cannot_run_lifecycle(auth_client, student_user):
    exam = add_questions(ExamFactory(status="draft"), mcq())
    other = UserFactory(role="faculty")
    assert auth_client(other).post(f"{API}/exams/{exam.pk}/schedule/").status_code == 404
    assert auth_client(student_user).post(f"{API}/exams/{exam.pk}/schedule/").status_code in (
        403,
        404,
    )


def test_delete_draft_without_attempts(auth_client, faculty_user):
    exam = add_questions(ExamFactory(created_by=faculty_user, status="draft"), mcq())
    assert auth_client(faculty_user).delete(f"{API}/exams/{exam.pk}/").status_code == 204
    assert not ExamQuestion.objects.exists()
