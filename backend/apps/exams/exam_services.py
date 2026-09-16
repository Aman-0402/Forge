"""Exam builder and lifecycle."""

import random

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_action
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .eligibility import eligible_students
from .models import Exam, ExamQuestion, Question
from .permissions import readable_banks

EDITABLE_AFTER_ATTEMPTS = {"title", "description", "reveal_answers"}


def has_attempts(exam):
    return exam.attempts.exists()


def ensure_no_attempts(exam, message="Students have already attempted this exam."):
    if has_attempts(exam):
        raise ValidationError({"detail": [message]})


def ensure_status(exam, *allowed):
    if exam.status not in allowed:
        raise ValidationError(
            {"status": [f"Exam is '{exam.status}'; this needs: {', '.join(allowed)}."]}
        )


def check_update_allowed(exam, fields):
    if has_attempts(exam) and not set(fields) <= EDITABLE_AFTER_ATTEMPTS:
        blocked = sorted(set(fields) - EDITABLE_AFTER_ATTEMPTS)
        raise ValidationError(
            {"detail": [f"Students have attempted this exam; cannot change: {', '.join(blocked)}."]}
        )


# ---------- questions ----------


def _usable_questions(user):
    return Question.objects.filter(bank__in=readable_banks(user), is_active=True)


@transaction.atomic
def add_questions(
    *, actor, exam, question_ids=(), bank=None, count=0, difficulty="", qtype="", request=None
):
    ensure_no_attempts(exam, "Students have attempted this exam; questions are locked.")
    existing = set(exam.exam_questions.values_list("question_id", flat=True))
    usable = _usable_questions(actor)

    chosen = []
    if question_ids:
        ids = list(dict.fromkeys(question_ids))
        found = {q.pk: q for q in usable.filter(pk__in=ids)}
        missing = [pk for pk in ids if pk not in found]
        if missing:
            raise ValidationError(
                {"question_ids": [f"Not available to you or inactive: {missing}."]}
            )
        dupes = [pk for pk in ids if pk in existing]
        if dupes:
            raise ValidationError({"question_ids": [f"Already in this exam: {dupes}."]})
        chosen = [found[pk] for pk in ids]
    elif bank:
        pool = usable.filter(bank_id=bank).exclude(pk__in=existing)
        if difficulty:
            pool = pool.filter(difficulty=difficulty)
        if qtype:
            pool = pool.filter(type=qtype)
        pool = list(pool)
        if len(pool) < count:
            raise ValidationError(
                {"count": [f"Only {len(pool)} matching questions are available in that bank."]}
            )
        chosen = random.SystemRandom().sample(pool, count)
    else:
        raise ValidationError({"detail": ["Give question_ids, or bank and count."]})

    start = (exam.exam_questions.aggregate(m=Max("order"))["m"] or -1) + 1
    created = ExamQuestion.objects.bulk_create(
        [ExamQuestion(exam=exam, question=q, order=start + i) for i, q in enumerate(chosen)]
    )
    log_action(
        actor,
        "exam.questions.add",
        target=exam,
        metadata={"question_ids": [q.pk for q in chosen]},
        request=request,
    )
    return created


# ---------- lifecycle ----------


@transaction.atomic
def schedule(*, actor, exam, request=None):
    ensure_status(exam, Exam.Status.DRAFT)
    if not exam.exam_questions.exists():
        raise ValidationError({"detail": ["Add at least one question before scheduling."]})
    if exam.ends_at <= timezone.now():
        raise ValidationError({"ends_at": ["The exam window has already ended."]})
    exam.status = Exam.Status.SCHEDULED
    exam.save(update_fields=["status", "updated_at"])
    log_action(actor, "exam.schedule", target=exam, request=request)
    notify(
        eligible_students(exam),
        f"Exam scheduled: {exam.title}",
        f"Opens {exam.starts_at:%d %b %Y %H:%M} UTC, closes {exam.ends_at:%d %b %Y %H:%M} UTC. "
        f"Duration {exam.duration_minutes} minutes.",
        kind=Notification.Kind.EXAM,
        link=f"/exams/{exam.pk}",
    )
    return exam


@transaction.atomic
def unschedule(*, actor, exam, request=None):
    ensure_status(exam, Exam.Status.SCHEDULED)
    ensure_no_attempts(exam)
    exam.status = Exam.Status.DRAFT
    exam.save(update_fields=["status", "updated_at"])
    log_action(actor, "exam.unschedule", target=exam, request=request)
    return exam


@transaction.atomic
def extend(*, actor, exam, ends_at, request=None):
    ensure_status(exam, Exam.Status.SCHEDULED)
    if ends_at <= exam.ends_at:
        raise ValidationError({"ends_at": ["The new end must be later than the current end."]})
    previous = exam.ends_at
    exam.ends_at = ends_at
    exam.save(update_fields=["ends_at", "updated_at"])
    log_action(
        actor,
        "exam.extend",
        target=exam,
        metadata={"from": previous.isoformat(), "to": ends_at.isoformat()},
        request=request,
    )
    return exam


def ensure_deletable(exam):
    ensure_status(exam, Exam.Status.DRAFT)
    ensure_no_attempts(exam)
