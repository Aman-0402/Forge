import logging

from django.conf import settings
from django.core.mail import send_mass_mail
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)


def notify(users, title, body="", kind=Notification.Kind.INFO, link="", email=False):
    """Create in-portal notifications for ``users`` and optionally email active users.

    ``users`` may be a list or queryset; duplicates are removed. Returns the created
    rows (primary keys are populated on MariaDB/PostgreSQL bulk inserts).
    """
    unique = list({u.pk: u for u in users}.values())
    if not unique:
        return []
    rows = Notification.objects.bulk_create(
        [Notification(recipient=u, title=title, body=body, kind=kind, link=link) for u in unique],
        batch_size=500,
    )
    if email:
        _send_emails(unique, title, body)
    return rows


def _send_emails(users, subject, body):
    messages = [
        (subject, body, settings.DEFAULT_FROM_EMAIL, [u.email])
        for u in users
        if u.is_active and u.email
    ]
    if not messages:
        return
    try:
        send_mass_mail(messages, fail_silently=False)
    except Exception:  # email must never break the request
        logger.exception("Failed to send %d notification emails", len(messages))


def mark_read(notification):
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification


def mark_all_read(user):
    return Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
