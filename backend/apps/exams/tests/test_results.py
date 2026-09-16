from decimal import Decimal

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.exams.models import Answer, Attempt
from apps.exams.tests.factories import ExamFactory, add_questions, mcq, subjective
from apps.notifications.models import Notification

API = "/api/v1"

pytestmark = pytest.mark.django_db


@pytest.fixture
def exam(faculty_user):
    e = ExamFactory(created_by=faculty_user, pass_marks=Decimal("6"), reveal_answers=True)
    add_questions(e, mcq(correct=(1,), marks=2, explanation="B is right"), subjective(marks=8))
    return e


def rows(exam):
    return list(exam.exam_questions.select_related("question").order_by("order"))


def take(auth_client, student, exam, pick=1, essay="My essay"):
    client = auth_client(student)
    attempt_id = client.post(f"{API}/exams/{exam.pk}/start/").data["id"]
    first, second = rows(exam)
    opts = list(first.question.options.order_by("order").values_list("pk", flat=True))
    client.put(
        f"{API}/attempts/{attempt_id}/answers/{first.pk}/",
        {"selected_option_ids": [opts[pick]]},
        format="json",
    )
    client.put(
        f"{API}/attempts/{attempt_id}/answers/{second.pk}/", {"text_answer": essay}, format="json"
    )
    client.post(f"{API}/attempts/{attempt_id}/submit/")
    return Attempt.objects.get(pk=attempt_id)


def essay_answer(attempt):
    return Answer.objects.get(attempt=attempt, exam_question__question__type="subjective")


# ---------- grading queue ----------


def test_manager_lists_attempts_with_integrity_counts(
    auth_client, faculty_user, student_user, exam
):
    attempt = take(auth_client, student_user, exam)
    attempt.integrity_events.create(kind="tab_switch")
    res = auth_client(faculty_user).get(f"{API}/exams/{exam.pk}/attempts/", {"status": "grading"})
    assert res.status_code == 200
    row = res.data["results"][0]
    assert row["student_detail"]["email"] == student_user.email
    assert row["integrity_event_count"] == 1 and row["status"] == "grading"
    other = UserFactory(role="faculty")
    assert auth_client(other).get(f"{API}/exams/{exam.pk}/attempts/").status_code == 404
    assert auth_client(student_user).get(f"{API}/exams/{exam.pk}/attempts/").status_code == 403


def test_review_shows_answer_key_to_manager(auth_client, faculty_user, student_user, exam):
    attempt = take(auth_client, student_user, exam)
    res = auth_client(faculty_user).get(f"{API}/attempts/{attempt.pk}/review/")
    assert res.status_code == 200
    first = res.data["answers"][0]
    assert any(o["is_correct"] for o in first["options"])
    assert any(o["selected"] for o in first["options"])
    assert res.data["answers"][1]["text_answer"] == "My essay"
    assert auth_client(student_user).get(f"{API}/attempts/{attempt.pk}/review/").status_code == 404


def test_grade_subjective_completes_attempt(auth_client, faculty_user, student_user, exam):
    attempt = take(auth_client, student_user, exam)
    answer = essay_answer(attempt)
    url = f"{API}/answers/{answer.pk}/grade/"
    manager = auth_client(faculty_user)
    assert manager.patch(url, {"marks_awarded": "9"}, format="json").status_code == 400
    res = manager.patch(
        url, {"marks_awarded": "5", "grader_feedback": "Good structure"}, format="json"
    )
    assert res.status_code == 200, res.data
    attempt.refresh_from_db()
    assert attempt.status == "graded"
    assert attempt.total_score == Decimal("7.00") and attempt.passed is True
    assert AuditLog.objects.filter(action="exam.answer.grade").exists()
    regrade = manager.patch(url, {"marks_awarded": "3"}, format="json")
    assert regrade.status_code == 200
    attempt.refresh_from_db()
    assert attempt.total_score == Decimal("5.00") and attempt.passed is False


def test_cannot_grade_objective_or_in_progress(auth_client, faculty_user, student_user, exam):
    attempt = take(auth_client, student_user, exam)
    objective = Answer.objects.get(attempt=attempt, exam_question__question__type="mcq_single")
    manager = auth_client(faculty_user)
    assert (
        manager.patch(
            f"{API}/answers/{objective.pk}/grade/", {"marks_awarded": "1"}, format="json"
        ).status_code
        == 400
    )

    other = UserFactory(role="student")
    client = auth_client(other)
    live_id = client.post(f"{API}/exams/{exam.pk}/start/").data["id"]
    essay_eq = rows(exam)[1]
    client.put(
        f"{API}/attempts/{live_id}/answers/{essay_eq.pk}/", {"text_answer": "draft"}, format="json"
    )
    live_answer = Answer.objects.get(attempt_id=live_id, exam_question=essay_eq)
    assert (
        manager.patch(
            f"{API}/answers/{live_answer.pk}/grade/", {"marks_awarded": "1"}, format="json"
        ).status_code
        == 400
    )


def test_student_cannot_grade(auth_client, student_user, exam):
    attempt = take(auth_client, student_user, exam)
    res = auth_client(student_user).patch(
        f"{API}/answers/{essay_answer(attempt).pk}/grade/", {"marks_awarded": "8"}, format="json"
    )
    assert res.status_code in (403, 404)


# ---------- release & visibility ----------


def test_result_hidden_until_release(auth_client, faculty_user, student_user, exam):
    attempt = take(auth_client, student_user, exam)
    student = auth_client(student_user)
    assert student.get(f"{API}/attempts/{attempt.pk}/result/").status_code == 403

    manager = auth_client(faculty_user)
    blocked = manager.post(f"{API}/exams/{exam.pk}/release-results/")
    assert blocked.status_code == 400

    manager.patch(
        f"{API}/answers/{essay_answer(attempt).pk}/grade/", {"marks_awarded": "6"}, format="json"
    )
    res = manager.post(f"{API}/exams/{exam.pk}/release-results/")
    assert res.status_code == 200 and res.data["results_released_at"]
    assert Notification.objects.filter(recipient=student_user, kind="result").exists()

    result = student.get(f"{API}/attempts/{attempt.pk}/result/")
    assert result.status_code == 200
    assert result.data["total_score"] == "8.00" and result.data["passed"] is True
    first = result.data["answers"][0]
    assert first["explanation"] == "B is right"
    assert first["correct_option_ids"]


def test_answers_hidden_when_reveal_off(auth_client, faculty_user, student_user, exam):
    exam.reveal_answers = False
    exam.save()
    attempt = take(auth_client, student_user, exam)
    manager = auth_client(faculty_user)
    manager.patch(
        f"{API}/answers/{essay_answer(attempt).pk}/grade/", {"marks_awarded": "4"}, format="json"
    )
    manager.post(f"{API}/exams/{exam.pk}/release-results/")
    result = auth_client(student_user).get(f"{API}/attempts/{attempt.pk}/result/").data
    body = str(result)
    assert "B is right" not in body and "correct_option_ids" not in body
    assert result["answers"][1]["grader_feedback"] == ""


def test_immediate_result_for_objective_only_exam(auth_client, faculty_user, student_user):
    e = add_questions(
        ExamFactory(created_by=faculty_user, show_result_immediately=True), mcq(marks=2)
    )
    client = auth_client(student_user)
    attempt_id = client.post(f"{API}/exams/{e.pk}/start/").data["id"]
    client.post(f"{API}/attempts/{attempt_id}/submit/")
    assert client.get(f"{API}/attempts/{attempt_id}/result/").status_code == 200


def test_other_student_cannot_read_result(auth_client, faculty_user, student_user, exam):
    attempt = take(auth_client, student_user, exam)
    manager = auth_client(faculty_user)
    manager.patch(
        f"{API}/answers/{essay_answer(attempt).pk}/grade/", {"marks_awarded": "6"}, format="json"
    )
    manager.post(f"{API}/exams/{exam.pk}/release-results/")
    assert (
        auth_client(UserFactory(role="student"))
        .get(f"{API}/attempts/{attempt.pk}/result/")
        .status_code
        == 404
    )
    assert manager.get(f"{API}/attempts/{attempt.pk}/result/").status_code == 200


# ---------- summaries ----------


def test_results_summary_and_csv(auth_client, faculty_user, exam):
    manager = auth_client(faculty_user)
    for pick, marks in ((1, "6"), (0, "2")):
        student = UserFactory(role="student")
        attempt = take(auth_client, student, exam, pick=pick)
        manager.patch(
            f"{API}/answers/{essay_answer(attempt).pk}/grade/",
            {"marks_awarded": marks},
            format="json",
        )

    summary = manager.get(f"{API}/exams/{exam.pk}/results/").data
    assert summary["stats"]["graded"] == 2
    assert summary["stats"]["highest"] == "8.00" and summary["stats"]["lowest"] == "2.00"
    assert summary["stats"]["pass_rate"] == "50.00"
    assert len(summary["rows"]) == 2

    csv = manager.get(f"{API}/exams/{exam.pk}/results/export/")
    assert csv.status_code == 200 and csv["Content-Type"].startswith("text/csv")
    lines = csv.content.decode().strip().splitlines()
    assert lines[0].startswith("email,") and len(lines) == 3


def test_my_results(auth_client, faculty_user, student_user, exam):
    attempt = take(auth_client, student_user, exam)
    client = auth_client(student_user)
    rows_before = client.get(f"{API}/me/results/").data["results"]
    assert rows_before[0]["result_visible"] is False and rows_before[0]["total_score"] is None
    manager = auth_client(faculty_user)
    manager.patch(
        f"{API}/answers/{essay_answer(attempt).pk}/grade/", {"marks_awarded": "6"}, format="json"
    )
    manager.post(f"{API}/exams/{exam.pk}/release-results/")
    rows_after = client.get(f"{API}/me/results/").data["results"]
    assert rows_after[0]["result_visible"] is True and rows_after[0]["total_score"] == "8.00"
    assert auth_client(faculty_user).get(f"{API}/me/results/").status_code == 403
