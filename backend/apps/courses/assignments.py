"""Assignment lifecycle: create, submit, grade."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import log_action
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import AssignmentSubmission, Enrollment
from .permissions import ACTIVE_ENROLLMENT, get_enrollment


def notify_new_assignment(assignment):
    students = [
        e.student
        for e in Enrollment.objects.filter(
            course=assignment.course, status__in=ACTIVE_ENROLLMENT
        ).select_related("student")
    ]
    due = f" Due {assignment.due_at:%d %b %Y %H:%M} UTC." if assignment.due_at else ""
    notify(
        students,
        f"New assignment: {assignment.title}",
        f"'{assignment.title}' was posted in {assignment.course.title}.{due}",
        kind=Notification.Kind.ASSIGNMENT,
        link=f"/courses/{assignment.course_id}/assignments/{assignment.pk}",
    )


@transaction.atomic
def submit(*, actor, assignment, file=None, text="", request=None):
    """Create or replace the student's submission. Returns ``(submission, created)``."""
    if get_enrollment(actor, assignment.course) is None:
        raise PermissionDenied("Only enrolled students can submit.")
    if not file and not (text or "").strip():
        raise ValidationError({"detail": ["Attach a file or write an answer."]})

    now = timezone.now()
    is_late = bool(assignment.due_at and now > assignment.due_at)
    if is_late and not assignment.allow_late:
        raise ValidationError({"detail": ["The due date has passed; late submissions are closed."]})

    submission = (
        AssignmentSubmission.objects.select_for_update()
        .filter(assignment=assignment, student=actor)
        .first()
    )
    created = submission is None
    if created:
        submission = AssignmentSubmission(assignment=assignment, student=actor)
    elif submission.graded_at:
        raise ValidationError({"detail": ["This submission is already graded."]})

    if file:
        submission.file = file
    submission.text = text or ""
    submission.submitted_at = now
    submission.is_late = is_late
    submission.save()
    log_action(
        actor,
        "assignment.submit",
        target=submission,
        metadata={"assignment": assignment.pk, "late": is_late, "resubmit": not created},
        request=request,
    )
    return submission, created


@transaction.atomic
def grade(*, actor, submission, marks, feedback="", request=None):
    if marks < 0 or marks > submission.assignment.max_marks:
        raise ValidationError(
            {"marks": [f"Marks must be between 0 and {submission.assignment.max_marks}."]}
        )
    submission.marks = marks
    submission.feedback = feedback or ""
    submission.graded_by = actor
    submission.graded_at = timezone.now()
    submission.save(update_fields=["marks", "feedback", "graded_by", "graded_at", "updated_at"])
    log_action(
        actor,
        "assignment.grade",
        target=submission,
        metadata={"marks": str(marks)},
        request=request,
    )
    assignment = submission.assignment
    notify(
        [submission.student],
        f"Graded: {assignment.title}",
        f"You scored {marks} / {assignment.max_marks}." + (f"\n\n{feedback}" if feedback else ""),
        kind=Notification.Kind.ASSIGNMENT,
        link=f"/courses/{assignment.course_id}/assignments/{assignment.pk}",
    )
    return submission
