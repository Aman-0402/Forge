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


def visible_announcements(user):
    """Admins see everything. Others see live posts for everyone, their role, their
    department, plus anything they authored."""
    qs = Announcement.objects.select_related("author", "department")
    if user.role == "admin":
        return qs
    now = timezone.now()
    audience = Q(audience=Announcement.Audience.ALL)
    if user.role in ROLE_AUDIENCE:
        audience |= Q(audience=ROLE_AUDIENCE[user.role])
    if user.department_id:
        audience |= Q(audience=Announcement.Audience.DEPARTMENT, department_id=user.department_id)
    live = Q(published_at__lte=now) & (Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    return qs.filter((audience & live) | Q(author=user))


def recipients(announcement):
    qs = User.objects.filter(is_active=True).exclude(pk=announcement.author_id)
    audience = announcement.audience
    if audience == Announcement.Audience.STUDENTS:
        qs = qs.filter(role="student")
    elif audience == Announcement.Audience.FACULTY:
        qs = qs.filter(role="faculty")
    elif audience == Announcement.Audience.DEPARTMENT:
        qs = qs.filter(department_id=announcement.department_id)
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
