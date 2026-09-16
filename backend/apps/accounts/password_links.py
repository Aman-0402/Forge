"""One-time set-password links for invites, admin resets and forgotten passwords.

Tokens come from Django's ``default_token_generator``: they embed the password hash and
last login, so a link stops working as soon as it is used or the password changes, and
expires after ``PASSWORD_RESET_TIMEOUT``.
"""

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.notifications.models import Notification
from apps.notifications.services import notify

from .services import change_password

User = get_user_model()


def build_link(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}/set-password?{urlencode({'uid': uid, 'token': token})}"


def user_for_link(uid, token):
    """Return the active user the link belongs to, or None if the link is invalid."""
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=pk, is_active=True)
    except (ValueError, TypeError, OverflowError, User.DoesNotExist):
        return None
    return user if default_token_generator.check_token(user, token) else None


def hours_valid():
    return settings.PASSWORD_RESET_TIMEOUT // 3600


def send_link(user, *, purpose):
    """Email and notify a set-password link. ``purpose`` is invite, reset or forgot."""
    link = build_link(user)
    titles = {
        "invite": "Your Forge LMS account is ready",
        "reset": "Your Forge LMS password was reset",
        "forgot": "Reset your Forge LMS password",
    }
    intros = {
        "invite": f"An account was created for {user.email} with role '{user.role}'.",
        "reset": "An administrator reset your password.",
        "forgot": "Someone asked to reset the password for this account. "
        "If it wasn't you, ignore this message.",
    }
    body = (
        f"{intros[purpose]}\n\n"
        f"Choose your password here: {link}\n"
        f"The link works once and expires in {hours_valid()} hours."
    )
    notify([user], titles[purpose], body, kind=Notification.Kind.ACCOUNT, email=True)
    return link


@transaction.atomic
def set_password_from_link(user, new_password):
    return change_password(user, new_password)
