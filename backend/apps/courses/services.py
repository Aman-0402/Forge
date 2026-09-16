"""Course lifecycle: approval flow, archive, delete."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_action
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Course

User = get_user_model()


def _instructors(course):
    return [course.instructor, *course.co_instructors.all()]


def _require_status(course, *allowed):
    if course.status not in allowed:
        names = ", ".join(allowed)
        raise ValidationError(
            {"status": [f"Course is '{course.status}'; this action needs: {names}."]}
        )


@transaction.atomic
def submit_for_approval(*, actor, course, request=None):
    _require_status(course, Course.Status.DRAFT)
    course.status = Course.Status.PENDING
    course.submitted_at = timezone.now()
    course.rejection_reason = ""
    course.save(update_fields=["status", "submitted_at", "rejection_reason", "updated_at"])
    log_action(actor, "course.submit", target=course, request=request)
    notify(
        User.objects.filter(role="admin", is_active=True),
        f"Course awaiting approval: {course.title}",
        f"{actor.email} submitted '{course.title}' for approval.",
        kind=Notification.Kind.INFO,
        link=f"/courses/{course.pk}",
    )
    return course


@transaction.atomic
def approve(*, actor, course, request=None):
    _require_status(course, Course.Status.DRAFT, Course.Status.PENDING)
    course.status = Course.Status.PUBLISHED
    course.approved_by = actor
    course.approved_at = timezone.now()
    course.rejection_reason = ""
    course.save(
        update_fields=["status", "approved_by", "approved_at", "rejection_reason", "updated_at"]
    )
    log_action(actor, "course.approve", target=course, request=request)
    notify(
        _instructors(course),
        f"Course published: {course.title}",
        f"'{course.title}' is now published.",
        kind=Notification.Kind.INFO,
        link=f"/courses/{course.pk}",
    )
    from .enrollment import sync_auto_enrollments

    sync_auto_enrollments(course, actor=actor)
    return course


@transaction.atomic
def reject(*, actor, course, reason, request=None):
    _require_status(course, Course.Status.PENDING)
    if not (reason or "").strip():
        raise ValidationError({"reason": ["A reason is required."]})
    course.status = Course.Status.DRAFT
    course.rejection_reason = reason.strip()
    course.save(update_fields=["status", "rejection_reason", "updated_at"])
    log_action(actor, "course.reject", target=course, metadata={"reason": reason}, request=request)
    notify(
        _instructors(course),
        f"Course changes requested: {course.title}",
        reason.strip(),
        kind=Notification.Kind.INFO,
        link=f"/courses/{course.pk}",
    )
    return course


@transaction.atomic
def archive(*, actor, course, request=None):
    _require_status(course, Course.Status.DRAFT, Course.Status.PENDING, Course.Status.PUBLISHED)
    course.status = Course.Status.ARCHIVED
    course.save(update_fields=["status", "updated_at"])
    log_action(actor, "course.archive", target=course, request=request)
    return course


def ensure_deletable(course):
    if course.status != Course.Status.DRAFT or course.enrollments.exists():
        raise ValidationError(
            {"detail": ["Only draft courses without enrollments can be deleted. Archive instead."]}
        )
