"""Aggregate counts for the admin analytics dashboard. One query per chart, kept
as simple .values().annotate(Count()) group-bys — the platform is small enough
that this doesn't need caching or a separate reporting store yet."""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from apps.coding.models import CodeSubmission, Problem
from apps.courses.models import Course, Enrollment
from apps.exams.models import Attempt
from apps.notifications.models import ContactMessage

User = get_user_model()

TOP_COURSES_LIMIT = 8


def _counts(queryset, field):
    """A uniform {label, count} breakdown by ``field`` — one shape for every chart."""
    rows = queryset.values(field).annotate(count=Count("id")).order_by(field)
    return [{"label": row[field], "count": row["count"]} for row in rows]


def overview():
    users_active = User.objects.aggregate(
        active=Count("id", filter=Q(is_active=True)),
        inactive=Count("id", filter=Q(is_active=False)),
    )

    # Aggregate kwarg names must not collide with the "passed" field they filter on,
    # or Django's aggregate resolver mistakes the alias for the field (FieldError).
    attempt_counts = Attempt.objects.aggregate(
        n_passed=Count("id", filter=Q(status=Attempt.Status.GRADED, passed=True)),
        n_failed=Count("id", filter=Q(status=Attempt.Status.GRADED, passed=False)),
        n_ungraded=Count("id", filter=~Q(status=Attempt.Status.GRADED)),
    )
    attempts = {
        "passed": attempt_counts["n_passed"],
        "failed": attempt_counts["n_failed"],
        "ungraded": attempt_counts["n_ungraded"],
    }

    # Active enrollments only — a completed or dropped enrollment shouldn't inflate
    # "how many students are currently taking this course".
    top_courses = (
        Course.objects.annotate(
            enrolled=Count("enrollments", filter=Q(enrollments__status=Enrollment.Status.ACTIVE))
        )
        .filter(enrolled__gt=0)
        .order_by("-enrolled")[:TOP_COURSES_LIMIT]
    )

    submitted_verdicts = CodeSubmission.objects.exclude(verdict="")

    return {
        "generated_at": timezone.now(),
        "users_by_role": _counts(User.objects, "role"),
        "users_active": users_active,
        "courses_by_status": _counts(Course.objects, "status"),
        "enrollments_by_status": _counts(Enrollment.objects, "status"),
        "top_courses_by_enrollment": [
            {"course": c.title, "code": c.code, "count": c.enrolled} for c in top_courses
        ],
        "exam_pass_fail": attempts,
        "coding_submissions_by_verdict": _counts(submitted_verdicts, "verdict"),
        "problems_by_difficulty": _counts(Problem.objects, "difficulty"),
        "contact_messages_total": ContactMessage.objects.count(),
    }
