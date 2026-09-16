"""Exam attempts: start, answer, submit, objective grading, totals.

Timing is server-authoritative. ``deadline_at`` is fixed when the attempt starts; answers
are accepted until ``deadline_at + EXAM_GRACE_SECONDS``. Any request that touches an
overdue in-progress attempt submits it first.
"""

import random
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import client_ip, log_action

from .eligibility import is_eligible
from .models import Answer, Attempt, Exam, ExamQuestion, Option, Question

User = get_user_model()
ZERO = Decimal("0")


def grace():
    return timedelta(seconds=getattr(settings, "EXAM_GRACE_SECONDS", 10))


def is_overdue(attempt, now=None):
    return (now or timezone.now()) > attempt.deadline_at + grace()


def seconds_remaining(attempt, now=None):
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return 0
    delta = attempt.deadline_at - (now or timezone.now())
    return max(0, int(delta.total_seconds()))


# ---------- start ----------


def start_attempt(*, student, exam, request=None):
    """Return ``(attempt, created)``. Resumes an in-progress attempt when one exists."""
    if student.role != "student":
        raise PermissionDenied("Only students can take exams.")
    if exam.status != Exam.Status.SCHEDULED:
        raise ValidationError({"detail": ["This exam is not open."]})
    if exam.phase == "upcoming":
        raise ValidationError(
            {"detail": [f"This exam opens at {exam.starts_at:%d %b %Y %H:%M} UTC."]}
        )
    if exam.phase == "ended":
        raise ValidationError({"detail": ["This exam has ended."]})
    if not is_eligible(student, exam):
        raise PermissionDenied("You are not eligible for this exam.")

    expire_overdue_for(student, exam)

    with transaction.atomic():
        # Serialise concurrent "start" clicks from the same student.
        User.objects.select_for_update().only("pk").get(pk=student.pk)
        current = Attempt.objects.filter(
            exam=exam, student=student, status=Attempt.Status.IN_PROGRESS
        ).first()
        if current:
            return current, False

        used = Attempt.objects.filter(exam=exam, student=student).count()
        if used >= exam.max_attempts:
            raise ValidationError({"detail": ["You have used all attempts for this exam."]})

        rows = list(
            exam.exam_questions.select_related("question").prefetch_related("question__options")
        )
        rng = random.SystemRandom()
        order = [eq.pk for eq in rows]
        if exam.shuffle_questions:
            rng.shuffle(order)
        option_orders = {}
        for eq in rows:
            ids = [o.pk for o in eq.question.options.all()]
            if exam.shuffle_options and eq.question.type != Question.Type.TRUE_FALSE:
                rng.shuffle(ids)
            option_orders[str(eq.pk)] = ids

        now = timezone.now()
        attempt = Attempt.objects.create(
            exam=exam,
            student=student,
            attempt_number=used + 1,
            started_at=now,
            deadline_at=min(now + timedelta(minutes=exam.duration_minutes), exam.ends_at),
            question_order=order,
            option_orders=option_orders,
            ip=client_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300] if request else ""),
        )
    log_action(
        student,
        "exam.attempt.start",
        target=attempt,
        metadata={"exam": exam.pk, "attempt_number": attempt.attempt_number},
        request=request,
    )
    return attempt, True


# ---------- answers ----------


def expire_if_overdue(attempt):
    """Submit an overdue in-progress attempt. Returns True if it was submitted now."""
    if attempt.status == Attempt.Status.IN_PROGRESS and is_overdue(attempt):
        try:
            submit_attempt(attempt=attempt, auto=True)
        except ValidationError:
            pass  # someone else submitted it concurrently
        attempt.refresh_from_db()
        return True
    return False


def expire_overdue_for(student, exam):
    for attempt in Attempt.objects.filter(
        exam=exam, student=student, status=Attempt.Status.IN_PROGRESS
    ):
        expire_if_overdue(attempt)


def save_answer(*, attempt, exam_question_id, selected_option_ids=(), text_answer=""):
    if expire_if_overdue(attempt):
        raise ValidationError({"detail": ["Time is up. Your attempt was submitted."]})

    with transaction.atomic():
        attempt = Attempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.status != Attempt.Status.IN_PROGRESS:
            raise ValidationError({"detail": ["This attempt is already submitted."]})
        try:
            eq = ExamQuestion.objects.select_related("question").get(
                pk=exam_question_id, exam=attempt.exam_id
            )
        except ExamQuestion.DoesNotExist as exc:
            raise ValidationError({"exam_question": ["Not part of this exam."]}) from exc

        question = eq.question
        chosen = list(dict.fromkeys(selected_option_ids))
        if question.is_objective:
            valid = set(Option.objects.filter(question=question).values_list("pk", flat=True))
            if not set(chosen) <= valid:
                raise ValidationError(
                    {"selected_option_ids": ["Those options do not belong to this question."]}
                )
            if question.type != Question.Type.MCQ_MULTI and len(chosen) > 1:
                raise ValidationError({"selected_option_ids": ["Choose only one option."]})
            text_answer = ""
        elif chosen:
            raise ValidationError(
                {"selected_option_ids": ["Written questions take a text answer."]}
            )

        answer, _ = Answer.objects.get_or_create(attempt=attempt, exam_question=eq)
        answer.text_answer = text_answer or ""
        answer.answered_at = timezone.now()
        answer.save(update_fields=["text_answer", "answered_at", "updated_at"])
        answer.selected_options.set(chosen)
    return answer


# ---------- submit & grading ----------


def grade_objective(answer, eq, chosen_ids):
    question = eq.question
    correct = {o.pk for o in question.options.all() if o.is_correct}
    chosen = set(chosen_ids)
    if not chosen:
        answer.is_correct, answer.marks_awarded = False, ZERO
    elif chosen == correct:
        answer.is_correct, answer.marks_awarded = True, eq.marks
    else:
        answer.is_correct, answer.marks_awarded = False, -question.negative_marks


def submit_attempt(*, attempt, auto=False, request=None):
    with transaction.atomic():
        attempt = Attempt.objects.select_for_update().select_related("exam").get(pk=attempt.pk)
        if attempt.status != Attempt.Status.IN_PROGRESS:
            raise ValidationError({"detail": ["This attempt is already submitted."]})

        rows = {
            eq.pk: eq
            for eq in ExamQuestion.objects.filter(exam=attempt.exam_id)
            .select_related("question")
            .prefetch_related("question__options")
        }
        answers = {
            a.exam_question_id: a for a in attempt.answers.prefetch_related("selected_options")
        }
        missing = [Answer(attempt=attempt, exam_question_id=pk) for pk in rows if pk not in answers]
        for created in Answer.objects.bulk_create(missing):
            answers[created.exam_question_id] = created

        for pk, eq in rows.items():
            answer = answers[pk]
            if eq.question.is_objective:
                chosen = [o.pk for o in answer.selected_options.all()] if answer.pk else []
                grade_objective(answer, eq, chosen)
            elif not answer.text_answer.strip():
                answer.is_correct, answer.marks_awarded = None, ZERO
            else:
                answer.is_correct, answer.marks_awarded = None, None
        Answer.objects.bulk_update(list(answers.values()), ["is_correct", "marks_awarded"])

        attempt.submitted_at = timezone.now()
        attempt.auto_submitted = auto
        attempt.save(update_fields=["submitted_at", "auto_submitted"])
        recompute_totals(attempt)

    log_action(
        None if auto else attempt.student,
        "exam.attempt.auto_submit" if auto else "exam.attempt.submit",
        target=attempt,
        metadata={
            "exam": attempt.exam_id,
            "score": str(attempt.total_score),
            "status": attempt.status,
        },
        request=None if auto else request,
    )
    return attempt


def exam_total_marks(exam_id):
    return sum(
        (eq.marks for eq in ExamQuestion.objects.filter(exam=exam_id).select_related("question")),
        ZERO,
    )


def recompute_totals(attempt):
    answers = list(attempt.answers.select_related("exam_question__question"))
    objective = sum(
        (a.marks_awarded or ZERO for a in answers if a.exam_question.question.is_objective), ZERO
    )
    subjective = sum(
        (a.marks_awarded or ZERO for a in answers if not a.exam_question.question.is_objective),
        ZERO,
    )
    pending = any(
        a.marks_awarded is None and not a.exam_question.question.is_objective for a in answers
    )
    total = max(ZERO, objective + subjective)
    possible = exam_total_marks(attempt.exam_id)
    percentage = (
        (total * 100 / possible).quantize(Decimal("0.01"), ROUND_HALF_UP) if possible else ZERO
    )

    attempt.objective_score = objective
    attempt.subjective_score = subjective
    attempt.total_score = total
    attempt.percentage = percentage
    attempt.status = Attempt.Status.GRADING if pending else Attempt.Status.GRADED
    pass_marks = attempt.exam.pass_marks
    attempt.passed = None if pending or pass_marks is None else total >= pass_marks
    attempt.save(
        update_fields=[
            "objective_score",
            "subjective_score",
            "total_score",
            "percentage",
            "status",
            "passed",
        ]
    )
    return attempt


# ---------- exam-wide ----------


def close_exam(*, actor, exam, request=None):
    from .exam_services import ensure_status

    ensure_status(exam, Exam.Status.SCHEDULED)
    exam.status = Exam.Status.CLOSED
    exam.save(update_fields=["status", "updated_at"])
    submitted = 0
    for attempt in Attempt.objects.filter(exam=exam, status=Attempt.Status.IN_PROGRESS):
        try:
            submit_attempt(attempt=attempt, auto=True)
            submitted += 1
        except ValidationError:
            pass
    log_action(
        actor, "exam.close", target=exam, metadata={"auto_submitted": submitted}, request=request
    )
    return exam


def sweep_overdue(now=None):
    cutoff = (now or timezone.now()) - grace()
    count = 0
    for attempt in Attempt.objects.filter(
        status=Attempt.Status.IN_PROGRESS, deadline_at__lt=cutoff
    ):
        try:
            submit_attempt(attempt=attempt, auto=True)
            count += 1
        except ValidationError:
            pass
    return count
