from django.db.models import Q
from django.utils import timezone

from .models import Problem

ACTIVE_ENROLLMENT = ("active", "completed")


def is_staff_role(user):
    return bool(user and user.is_authenticated and user.role in ("admin", "faculty"))


def can_manage_problem(user, problem):
    if not (user and user.is_authenticated):
        return False
    if user.role == "admin" or problem.created_by_id == user.pk:
        return True
    if problem.course_id:
        from apps.courses.permissions import can_manage_course

        return can_manage_course(user, problem.course)
    return False


def managed_problems_q(user):
    return Q(created_by=user) | Q(course__instructor=user) | Q(course__co_instructors=user)


def student_open_q(user):
    now = timezone.now()
    return (
        Q(status=Problem.Status.PUBLISHED)
        & (Q(visible_from__isnull=True) | Q(visible_from__lte=now))
        & (Q(visible_until__isnull=True) | Q(visible_until__gt=now))
        & (
            Q(course__isnull=True)
            | Q(
                course__enrollments__student=user, course__enrollments__status__in=ACTIVE_ENROLLMENT
            )
        )
    )


def visible_problems(user):
    qs = Problem.objects.all()
    if user.role == "admin":
        return qs
    if user.role == "faculty":
        return qs.filter(Q(status=Problem.Status.PUBLISHED) | managed_problems_q(user)).distinct()
    return qs.filter(student_open_q(user)).distinct()


def can_attempt_problem(user, problem):
    """Students may run/submit only on problems currently open to them."""
    return Problem.objects.filter(pk=problem.pk).filter(student_open_q(user)).exists()
