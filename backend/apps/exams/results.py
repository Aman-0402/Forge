"""Manual grading, result release, result payloads and summaries."""

import csv
import io
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_action
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .attempts import exam_total_marks, recompute_totals
from .models import Answer, Attempt, ExamQuestion

TWO = Decimal("0.01")


def fmt(value):
    return None if value is None else f"{Decimal(value).quantize(TWO, ROUND_HALF_UP)}"


# ---------- grading ----------


@transaction.atomic
def grade_answer(*, actor, answer, marks_awarded, grader_feedback="", request=None):
    answer = (
        Answer.objects.select_for_update()
        .select_related("attempt__exam", "exam_question__question")
        .get(pk=answer.pk)
    )
    question = answer.exam_question.question
    if question.is_objective:
        raise ValidationError({"detail": ["Objective answers are graded automatically."]})
    if answer.attempt.status == Attempt.Status.IN_PROGRESS:
        raise ValidationError({"detail": ["The student has not submitted this attempt yet."]})
    maximum = answer.exam_question.marks
    if marks_awarded < 0 or marks_awarded > maximum:
        raise ValidationError({"marks_awarded": [f"Must be between 0 and {maximum}."]})

    answer.marks_awarded = marks_awarded
    answer.grader_feedback = grader_feedback or ""
    answer.graded_by = actor
    answer.save(update_fields=["marks_awarded", "grader_feedback", "graded_by", "updated_at"])
    attempt = recompute_totals(answer.attempt)
    log_action(
        actor,
        "exam.answer.grade",
        target=answer,
        metadata={"attempt": attempt.pk, "marks": str(marks_awarded)},
        request=request,
    )
    return answer


@transaction.atomic
def release_results(*, actor, exam, request=None):
    pending = exam.attempts.filter(status=Attempt.Status.GRADING).count()
    if pending:
        raise ValidationError({"detail": [f"{pending} attempts still need grading."]})
    exam.results_released_at = timezone.now()
    exam.save(update_fields=["results_released_at", "updated_at"])
    graded = exam.attempts.filter(status=Attempt.Status.GRADED).select_related("student")
    students = list({a.student_id: a.student for a in graded}.values())
    log_action(
        actor,
        "exam.release_results",
        target=exam,
        metadata={"students": len(students)},
        request=request,
    )
    notify(
        students,
        f"Results released: {exam.title}",
        f"Your result for '{exam.title}' is available.",
        kind=Notification.Kind.RESULT,
        link=f"/exams/{exam.pk}",
    )
    return exam


# ---------- visibility & payloads ----------


def result_visible(attempt):
    if attempt.status == Attempt.Status.IN_PROGRESS:
        return False
    exam = attempt.exam
    if exam.results_released_at and attempt.status == Attempt.Status.GRADED:
        return True
    return exam.show_result_immediately and attempt.status == Attempt.Status.GRADED


def result_payload(attempt, *, reveal):
    exam = attempt.exam
    rows = {
        eq.pk: eq
        for eq in ExamQuestion.objects.filter(exam=exam)
        .select_related("question")
        .prefetch_related("question__options")
    }
    answers = {
        a.exam_question_id: a
        for a in attempt.answers.prefetch_related("selected_options").select_related("graded_by")
    }
    out = []
    for index, eq_pk in enumerate(attempt.question_order or list(rows), start=1):
        eq = rows.get(eq_pk)
        if eq is None:
            continue
        question = eq.question
        answer = answers.get(eq_pk)
        selected = [o.pk for o in answer.selected_options.all()] if answer else []
        item = {
            "answer_id": answer.pk if answer else None,
            "exam_question_id": eq_pk,
            "index": index,
            "type": question.type,
            "text": question.text,
            "marks": fmt(eq.marks),
            "options": [{"id": o.pk, "text": o.text} for o in question.options.all()],
            "selected_option_ids": selected,
            "text_answer": answer.text_answer if answer else "",
            "marks_awarded": fmt(answer.marks_awarded) if answer else None,
            "is_correct": answer.is_correct if answer else None,
            "grader_feedback": answer.grader_feedback if answer else "",
        }
        if reveal:
            item["correct_option_ids"] = [o.pk for o in question.options.all() if o.is_correct]
            item["explanation"] = question.explanation
        out.append(item)

    return {
        "id": attempt.pk,
        "exam": {"id": exam.pk, "title": exam.title, "pass_marks": fmt(exam.pass_marks)},
        "attempt_number": attempt.attempt_number,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "auto_submitted": attempt.auto_submitted,
        "objective_score": fmt(attempt.objective_score),
        "subjective_score": fmt(attempt.subjective_score),
        "total_score": fmt(attempt.total_score),
        "total_marks": fmt(exam_total_marks(exam.pk)),
        "percentage": fmt(attempt.percentage),
        "passed": attempt.passed,
        "answers": out,
    }


def review_payload(attempt):
    """Manager view: everything, including selections marked on each option."""
    data = result_payload(attempt, reveal=True)
    for item in data["answers"]:
        correct = set(item["correct_option_ids"])
        chosen = set(item["selected_option_ids"])
        item["options"] = [
            {**o, "is_correct": o["id"] in correct, "selected": o["id"] in chosen}
            for o in item["options"]
        ]
    data["student"] = {
        "id": attempt.student_id,
        "email": attempt.student.email,
        "name": attempt.student.get_full_name() or attempt.student.email,
    }
    data["integrity_events"] = [
        {"kind": e.kind, "occurred_at": e.occurred_at, "metadata": e.metadata}
        for e in attempt.integrity_events.all()
    ]
    return data


# ---------- summaries ----------


def summary(exam):
    graded = list(
        exam.attempts.filter(status=Attempt.Status.GRADED)
        .select_related("student__student_profile")
        .order_by("-total_score", "submitted_at")
    )
    scores = [a.total_score for a in graded]
    passed = [a for a in graded if a.passed]
    judged = [a for a in graded if a.passed is not None]
    stats = {
        "attempts": exam.attempts.count(),
        "in_progress": exam.attempts.filter(status=Attempt.Status.IN_PROGRESS).count(),
        "awaiting_grading": exam.attempts.filter(status=Attempt.Status.GRADING).count(),
        "graded": len(graded),
        "total_marks": fmt(exam_total_marks(exam.pk)),
        "average": fmt(sum(scores) / len(scores)) if scores else None,
        "highest": fmt(max(scores)) if scores else None,
        "lowest": fmt(min(scores)) if scores else None,
        "pass_rate": fmt(Decimal(len(passed)) * 100 / len(judged)) if judged else None,
    }
    rows = [
        {
            "attempt_id": a.pk,
            "student_id": a.student_id,
            "email": a.student.email,
            "name": a.student.get_full_name() or a.student.email,
            "roll_number": getattr(
                getattr(a.student, "student_profile", None), "roll_number", None
            ),
            "attempt_number": a.attempt_number,
            "total_score": fmt(a.total_score),
            "percentage": fmt(a.percentage),
            "passed": a.passed,
            "submitted_at": a.submitted_at,
            "auto_submitted": a.auto_submitted,
        }
        for a in graded
    ]
    return {"stats": stats, "rows": rows}


def export_csv(exam):
    data = summary(exam)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "email",
            "name",
            "roll_number",
            "attempt",
            "score",
            "total_marks",
            "percentage",
            "passed",
            "submitted_at",
            "auto_submitted",
        ]
    )
    for row in data["rows"]:
        writer.writerow(
            [
                row["email"],
                row["name"],
                row["roll_number"] or "",
                row["attempt_number"],
                row["total_score"],
                data["stats"]["total_marks"],
                row["percentage"],
                "" if row["passed"] is None else ("yes" if row["passed"] else "no"),
                row["submitted_at"].isoformat() if row["submitted_at"] else "",
                "yes" if row["auto_submitted"] else "no",
            ]
        )
    return buffer.getvalue()
