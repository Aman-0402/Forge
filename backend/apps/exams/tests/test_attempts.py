from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.courses.tests.factories import CourseFactory, EnrollmentFactory
from apps.exams.models import Attempt, IntegrityEvent
from apps.exams.tests.factories import (
    ExamFactory,
    add_questions,
    mcq,
    subjective,
    true_false,
)

API = "/api/v1"

pytestmark = pytest.mark.django_db


@pytest.fixture
def exam(faculty_user):
    """Live exam: q0 single (opt0 correct, -1 wrong), q1 multi (opt0+opt1), q2 true/false (True)."""
    e = ExamFactory(created_by=faculty_user, duration_minutes=30, pass_marks=Decimal("4"))
    add_questions(
        e,
        mcq(correct=(0,), marks=2, negative_marks=1),
        mcq(correct=(0, 1), type_="mcq_multi", marks=3),
        true_false(answer=True, marks=1),
    )
    return e


def start(client, exam):
    return client.post(f"{API}/exams/{exam.pk}/start/")


def eqs(exam):
    return list(exam.exam_questions.select_related("question").order_by("order"))


def option_ids(eq, *indexes):
    ids = list(eq.question.options.order_by("order").values_list("pk", flat=True))
    return [ids[i] for i in indexes]


def answer(client, attempt_id, eq, ids=(), text=""):
    return client.put(
        f"{API}/attempts/{attempt_id}/answers/{eq.pk}/",
        {"selected_option_ids": list(ids), "text_answer": text},
        format="json",
    )


# ---------- start ----------


def test_start_creates_attempt_without_answer_key(auth_client, student_user, exam):
    res = start(auth_client(student_user), exam)
    assert res.status_code == 201, res.data
    body = res.content.decode()
    assert "is_correct" not in body and "explanation" not in body
    assert len(res.data["questions"]) == 3
    assert res.data["seconds_remaining"] > 29 * 60
    attempt = Attempt.objects.get()
    assert attempt.deadline_at <= attempt.started_at + timedelta(minutes=30)
    assert AuditLog.objects.filter(action="exam.attempt.start").exists()


def test_deadline_capped_by_window(auth_client, student_user, faculty_user):
    e = add_questions(
        ExamFactory(
            created_by=faculty_user,
            duration_minutes=120,
            ends_at=timezone.now() + timedelta(minutes=10),
        ),
        mcq(),
    )
    start(auth_client(student_user), e)
    attempt = Attempt.objects.get()
    assert attempt.deadline_at == e.ends_at


def test_start_again_resumes_same_attempt_and_order(auth_client, student_user, faculty_user):
    e = ExamFactory(created_by=faculty_user, shuffle_questions=True, shuffle_options=True)
    add_questions(e, *[mcq() for _ in range(6)])
    client = auth_client(student_user)
    first = start(client, e)
    again = start(client, e)
    assert again.status_code == 200 and again.data["id"] == first.data["id"]
    get = client.get(f"{API}/attempts/{first.data['id']}/")
    assert [q["exam_question_id"] for q in get.data["questions"]] == [
        q["exam_question_id"] for q in first.data["questions"]
    ]
    assert [o["id"] for o in get.data["questions"][0]["options"]] == [
        o["id"] for o in first.data["questions"][0]["options"]
    ]


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"starts_at_delta": 60, "ends_at_delta": 120}, 400),
        ({"starts_at_delta": -120, "ends_at_delta": -60}, 400),
        ({"status": "closed"}, 400),
        ({"status": "draft"}, 404),
    ],
)
def test_start_outside_window_or_wrong_status(
    auth_client, student_user, faculty_user, overrides, code
):
    now = timezone.now()
    kwargs = {"created_by": faculty_user}
    if "starts_at_delta" in overrides:
        kwargs["starts_at"] = now + timedelta(minutes=overrides["starts_at_delta"])
        kwargs["ends_at"] = now + timedelta(minutes=overrides["ends_at_delta"])
    if "status" in overrides:
        kwargs["status"] = overrides["status"]
    e = add_questions(ExamFactory(**kwargs), mcq())
    assert start(auth_client(student_user), e).status_code == code


def test_start_requires_eligibility(auth_client, student_user, faculty_user):
    course = CourseFactory(instructor=faculty_user)
    e = add_questions(ExamFactory(created_by=faculty_user, course=course), mcq())
    client = auth_client(student_user)
    assert start(client, e).status_code in (403, 404)
    EnrollmentFactory(course=course, student=student_user)
    assert start(client, e).status_code == 201
    assert start(auth_client(faculty_user), e).status_code == 403


def test_max_attempts(auth_client, student_user, exam):
    client = auth_client(student_user)
    first = start(client, exam).data["id"]
    client.post(f"{API}/attempts/{first}/submit/")
    assert start(client, exam).status_code == 400
    exam.max_attempts = 2
    exam.save()
    res = start(client, exam)
    assert res.status_code == 201 and res.data["attempt_number"] == 2


# ---------- answers ----------


def test_save_answers_and_validation(auth_client, student_user, exam):
    client = auth_client(student_user)
    attempt_id = start(client, exam).data["id"]
    single, multi, tf = eqs(exam)

    assert answer(client, attempt_id, single, option_ids(single, 1)).status_code == 200
    assert answer(client, attempt_id, single, option_ids(single, 0)).status_code == 200
    assert answer(client, attempt_id, multi, option_ids(multi, 0, 1)).status_code == 200
    assert answer(client, attempt_id, single, option_ids(single, 0, 1)).status_code == 400
    assert answer(client, attempt_id, single, option_ids(multi, 0)).status_code == 400

    resumed = client.get(f"{API}/attempts/{attempt_id}/").data
    saved = {
        q["exam_question_id"]: q["answer"]["selected_option_ids"] for q in resumed["questions"]
    }
    assert saved[single.pk] == option_ids(single, 0)
    assert tf.pk in saved


def test_other_student_cannot_touch_attempt(auth_client, student_user, exam):
    attempt_id = start(auth_client(student_user), exam).data["id"]
    intruder = auth_client(UserFactory(role="student"))
    single = eqs(exam)[0]
    assert intruder.get(f"{API}/attempts/{attempt_id}/").status_code == 404
    assert answer(intruder, attempt_id, single, option_ids(single, 0)).status_code == 404
    assert intruder.post(f"{API}/attempts/{attempt_id}/submit/").status_code == 404


def test_answer_after_deadline_is_rejected_and_attempt_auto_submitted(
    auth_client, student_user, exam
):
    client = auth_client(student_user)
    with freeze_time(timezone.now()) as frozen:
        attempt_id = start(client, exam).data["id"]
        single = eqs(exam)[0]
        answer(client, attempt_id, single, option_ids(single, 0))
        frozen.tick(timedelta(minutes=30, seconds=5))
        assert answer(client, attempt_id, single, option_ids(single, 1)).status_code == 200
        frozen.tick(timedelta(seconds=10))
        assert answer(client, attempt_id, single, option_ids(single, 1)).status_code == 400
    attempt = Attempt.objects.get(pk=attempt_id)
    assert attempt.status != "in_progress" and attempt.auto_submitted
    assert attempt.objective_score == Decimal("-1") or attempt.total_score == Decimal("0")


# ---------- submit & objective grading ----------


def test_submit_grades_objective_questions(auth_client, student_user, exam):
    client = auth_client(student_user)
    attempt_id = start(client, exam).data["id"]
    single, multi, tf = eqs(exam)
    answer(client, attempt_id, single, option_ids(single, 0))  # +2
    answer(client, attempt_id, multi, option_ids(multi, 0, 1))  # +3
    answer(client, attempt_id, tf, option_ids(tf, 1))  # wrong, no negative -> 0

    res = client.post(f"{API}/attempts/{attempt_id}/submit/")
    assert res.status_code == 200, res.data
    attempt = Attempt.objects.get(pk=attempt_id)
    assert attempt.status == "graded"
    assert attempt.total_score == Decimal("5.00")
    assert attempt.percentage == Decimal("83.33")
    assert attempt.passed is True
    assert client.post(f"{API}/attempts/{attempt_id}/submit/").status_code == 400
    assert AuditLog.objects.filter(action="exam.attempt.submit").exists()


def test_negative_marks_partial_multi_and_unanswered(auth_client, student_user, exam):
    client = auth_client(student_user)
    attempt_id = start(client, exam).data["id"]
    single, multi, _tf = eqs(exam)
    answer(client, attempt_id, single, option_ids(single, 2))  # wrong -> -1
    answer(client, attempt_id, multi, option_ids(multi, 0))  # partial -> 0 (no negative)
    client.post(f"{API}/attempts/{attempt_id}/submit/")
    attempt = Attempt.objects.get(pk=attempt_id)
    marks = {a.exam_question_id: a.marks_awarded for a in attempt.answers.all()}
    assert marks[single.pk] == Decimal("-1") and marks[multi.pk] == Decimal("0")
    assert attempt.answers.count() == 3
    assert attempt.total_score == Decimal("0.00")
    assert attempt.passed is False


def test_subjective_leaves_attempt_awaiting_grading(auth_client, student_user, faculty_user):
    e = add_questions(
        ExamFactory(created_by=faculty_user), mcq(marks=2), subjective(marks=5), subjective(marks=5)
    )
    client = auth_client(student_user)
    attempt_id = start(client, e).data["id"]
    first, essay, skipped = eqs(e)
    answer(client, attempt_id, first, option_ids(first, 0))
    assert answer(client, attempt_id, essay, text="Recursion is...").status_code == 200
    client.post(f"{API}/attempts/{attempt_id}/submit/")
    attempt = Attempt.objects.get(pk=attempt_id)
    assert attempt.status == "grading" and attempt.passed is None
    marks = {a.exam_question_id: a.marks_awarded for a in attempt.answers.all()}
    assert marks[essay.pk] is None and marks[skipped.pk] == Decimal("0")


def test_get_after_submit_hides_questions(auth_client, student_user, exam):
    client = auth_client(student_user)
    attempt_id = start(client, exam).data["id"]
    client.post(f"{API}/attempts/{attempt_id}/submit/")
    data = client.get(f"{API}/attempts/{attempt_id}/").data
    assert data["status"] == "graded" and data["questions"] == []


# ---------- auto submit ----------


def test_lazy_auto_submit_on_read(auth_client, student_user, exam):
    client = auth_client(student_user)
    with freeze_time(timezone.now()) as frozen:
        attempt_id = start(client, exam).data["id"]
        frozen.tick(timedelta(minutes=45))
        data = client.get(f"{API}/attempts/{attempt_id}/").data
    assert data["status"] == "graded" and data["auto_submitted"] is True


def test_sweep_command_submits_overdue_attempts(auth_client, student_user, exam):
    client = auth_client(student_user)
    with freeze_time(timezone.now()) as frozen:
        attempt_id = start(client, exam).data["id"]
        other = UserFactory(role="student")
        fresh_id = start(auth_client(other), exam).data["id"]
        Attempt.objects.filter(pk=fresh_id).update(deadline_at=timezone.now() + timedelta(hours=5))
        frozen.tick(timedelta(hours=1))
        call_command("sweep_overdue_attempts")
    assert Attempt.objects.get(pk=attempt_id).auto_submitted is True
    assert Attempt.objects.get(pk=fresh_id).status == "in_progress"


def test_close_exam_submits_in_progress_and_blocks_new_starts(
    auth_client, faculty_user, student_user, exam
):
    attempt_id = start(auth_client(student_user), exam).data["id"]
    res = auth_client(faculty_user).post(f"{API}/exams/{exam.pk}/close/")
    assert res.status_code == 200 and res.data["status"] == "closed"
    assert Attempt.objects.get(pk=attempt_id).auto_submitted is True
    newcomer = auth_client(UserFactory(role="student"))
    assert start(newcomer, exam).status_code == 400


# ---------- integrity ----------


def test_integrity_events(auth_client, student_user, exam):
    client = auth_client(student_user)
    attempt_id = start(client, exam).data["id"]
    url = f"{API}/attempts/{attempt_id}/integrity-events/"
    res = client.post(url, {"kind": "tab_switch", "metadata": {"away_ms": 3000}}, format="json")
    assert res.status_code == 201
    assert client.post(url, {"kind": "hacking"}, format="json").status_code == 400
    client.post(f"{API}/attempts/{attempt_id}/submit/")
    assert client.post(url, {"kind": "tab_switch"}, format="json").status_code == 400
    assert IntegrityEvent.objects.count() == 1


def test_integrity_events_ignored_when_tracking_off(auth_client, student_user, exam):
    exam.integrity_tracking = False
    exam.save()
    client = auth_client(student_user)
    attempt_id = start(client, exam).data["id"]
    res = client.post(
        f"{API}/attempts/{attempt_id}/integrity-events/", {"kind": "copy"}, format="json"
    )
    assert res.status_code == 204
    assert IntegrityEvent.objects.count() == 0
