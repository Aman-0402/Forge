"""Lesson completion and course progress."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.audit.services import log_action
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Enrollment, Lesson, LessonProgress
from .permissions import ACTIVE_ENROLLMENT, get_enrollment


def total_lessons(course):
    return Lesson.objects.filter(chapter__module__course=course).count()


def completed_lesson_ids(enrollment):
    return sorted(
        LessonProgress.objects.filter(
            enrollment=enrollment,
            completed_at__isnull=False,
            lesson__chapter__module__course_id=enrollment.course_id,
        ).values_list("lesson_id", flat=True)
    )


def recompute_enrollment(enrollment, total=None, actor=None, request=None):
    total = total_lessons(enrollment.course) if total is None else total
    done = len(completed_lesson_ids(enrollment))
    percent = min(100, round(done * 100 / total)) if total else 0
    fields = ["progress_percent", "updated_at"]
    enrollment.progress_percent = percent

    finished_now = percent == 100 and enrollment.status == Enrollment.Status.ACTIVE
    if finished_now:
        enrollment.status = Enrollment.Status.COMPLETED
        enrollment.completed_at = timezone.now()
        fields += ["status", "completed_at"]
    enrollment.save(update_fields=fields)

    if finished_now:
        log_action(actor, "enrollment.complete", target=enrollment, request=request)
        notify(
            [enrollment.student],
            f"Completed: {enrollment.course.title}",
            f"Congratulations! You finished '{enrollment.course.title}'.",
            kind=Notification.Kind.ENROLLMENT,
            link=f"/courses/{enrollment.course_id}",
        )
    return enrollment


def recompute_course_progress(course):
    """Call after lessons are added or removed."""
    total = total_lessons(course)
    enrollments = Enrollment.objects.filter(course=course, status__in=ACTIVE_ENROLLMENT)
    for enrollment in enrollments.select_related("course", "student"):
        recompute_enrollment(enrollment, total=total)


def _enrollment_for(actor, lesson):
    course = lesson.chapter.module.course
    enrollment = get_enrollment(actor, course)
    if enrollment is None:
        raise PermissionDenied("Only enrolled students can track progress in this course.")
    return enrollment


@transaction.atomic
def complete_lesson(*, actor, lesson, request=None):
    enrollment = _enrollment_for(actor, lesson)
    progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
    if progress.completed_at is None:
        progress.completed_at = timezone.now()
        progress.save(update_fields=["completed_at", "updated_at"])
    return recompute_enrollment(enrollment, actor=actor, request=request)


@transaction.atomic
def save_position(*, actor, lesson, seconds):
    enrollment = _enrollment_for(actor, lesson)
    progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
    progress.last_position_seconds = seconds
    progress.save(update_fields=["last_position_seconds", "updated_at"])
    return progress
