"""Aggregate counts for the admin analytics dashboard. One query per chart, kept
as simple .values().annotate(Count()) group-bys — the platform is small enough
that this doesn't need caching or a separate reporting store yet."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.coding.models import CodeSubmission, Problem
from apps.courses.models import Course, Enrollment
from apps.exams.models import Attempt
from apps.notifications.models import ContactMessage

User = get_user_model()

TOP_COURSES_LIMIT = 8
TIMESERIES_MIN_DAYS = 1
TIMESERIES_MAX_DAYS = 180
TIMESERIES_DEFAULT_DAYS = 30


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


def clamp_days(raw):
    """Parse a ?days= query param into a safe int, silently falling back to the
    default on anything invalid rather than 400ing over a cosmetic filter."""
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return TIMESERIES_DEFAULT_DAYS
    return max(TIMESERIES_MIN_DAYS, min(TIMESERIES_MAX_DAYS, days))


def _daily_counts(queryset, date_field):
    rows = queryset.annotate(day=TruncDate(date_field)).values("day").annotate(count=Count("id"))
    return {row["day"]: row["count"] for row in rows}


def timeseries(days=TIMESERIES_DEFAULT_DAYS):
    """Daily activity counts for the trend line chart, oldest day first."""
    days = clamp_days(days)
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    window_start = timezone.make_aware(
        timezone.datetime.combine(start, timezone.datetime.min.time())
    )

    by_day = {
        "new_users": _daily_counts(
            User.objects.filter(date_joined__gte=window_start), "date_joined"
        ),
        "new_enrollments": _daily_counts(
            Enrollment.objects.filter(created_at__gte=window_start), "created_at"
        ),
        "exam_attempts": _daily_counts(
            Attempt.objects.filter(started_at__gte=window_start), "started_at"
        ),
        "code_submissions": _daily_counts(
            CodeSubmission.objects.filter(submitted_at__gte=window_start), "submitted_at"
        ),
    }

    result = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        result.append(
            {
                "date": day.isoformat(),
                **{metric: counts.get(day, 0) for metric, counts in by_day.items()},
            }
        )
    return {"days": result}
