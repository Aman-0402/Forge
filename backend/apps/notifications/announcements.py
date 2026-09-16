"""Announcement audience rules, visibility and delivery."""

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from .models import Announcement, Notification
from .services import notify

User = get_user_model()

ROLE_AUDIENCE = {
    "student": Announcement.Audience.STUDENTS,
    "faculty": Announcement.Audience.FACULTY,
}


def _user_course_ids(user):
    """Courses whose announcements this user may read: enrolled or teaching."""
    from apps.courses.models import Course, Enrollment
    from apps.courses.permissions import ACTIVE_ENROLLMENT

    if user.role == "student":
        return Enrollment.objects.filter(student=user, status__in=ACTIVE_ENROLLMENT).values(
            "course_id"
        )
    if user.role == "faculty":
        return Course.objects.filter(Q(instructor=user) | Q(co_instructors=user)).values("pk")
    return Course.objects.none().values("pk")


def visible_announcements(user):
    """Admins see everything. Others see live posts for everyone, their role, their
    department, their courses, plus anything they authored."""
    qs = Announcement.objects.select_related("author", "department", "course")
    if user.role == "admin":
        return qs
    now = timezone.now()
    audience = Q(audience=Announcement.Audience.ALL)
    if user.role in ROLE_AUDIENCE:
        audience |= Q(audience=ROLE_AUDIENCE[user.role])
    if user.department_id:
        audience |= Q(audience=Announcement.Audience.DEPARTMENT, department_id=user.department_id)
    audience |= Q(audience=Announcement.Audience.COURSE, course_id__in=_user_course_ids(user))
    live = Q(published_at__lte=now) & (Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    return qs.filter((audience & live) | Q(author=user)).distinct()


def recipients(announcement):
    qs = User.objects.filter(is_active=True).exclude(pk=announcement.author_id)
    audience = announcement.audience
    if audience == Announcement.Audience.STUDENTS:
        return qs.filter(role="student")
    if audience == Announcement.Audience.FACULTY:
        return qs.filter(role="faculty")
    if audience == Announcement.Audience.DEPARTMENT:
        return qs.filter(department_id=announcement.department_id)
    if audience == Announcement.Audience.COURSE:
        from apps.courses.models import Enrollment
        from apps.courses.permissions import ACTIVE_ENROLLMENT

        course = announcement.course
        enrolled = Enrollment.objects.filter(course=course, status__in=ACTIVE_ENROLLMENT).values(
            "student_id"
        )
        teachers = [course.instructor_id, *course.co_instructors.values_list("pk", flat=True)]
        return qs.filter(Q(pk__in=enrolled) | Q(pk__in=teachers)).distinct()
    return qs


def deliver(announcement):
    """Send in-portal notifications if the announcement is already published."""
    if announcement.published_at > timezone.now():
        return []
    return notify(
        recipients(announcement),
        f"Announcement: {announcement.title}",
        announcement.body,
        kind=Notification.Kind.ANNOUNCEMENT,
        link=f"/announcements/{announcement.pk}",
    )
