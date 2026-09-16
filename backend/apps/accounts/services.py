from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@transaction.atomic
def register_student(*, email, password, first_name="", last_name=""):
    """Self-registration always yields a student, regardless of input."""
    return User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=User.Role.STUDENT,
    )


def revoke_tokens(user):
    """End every session: blacklist refresh tokens and reject older access tokens."""
    for token in OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True):
        BlacklistedToken.objects.get_or_create(token=token)
    user.tokens_valid_after = timezone.now()
    user.save(update_fields=["tokens_valid_after", "updated_at"])


def issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


@transaction.atomic
def change_password(user, new_password):
    """Set a new password, end all other sessions and return a fresh token pair."""
    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "updated_at"])
    revoke_tokens(user)
    return issue_tokens(user)


def blacklist_refresh_token(raw_token):
    """Return True if blacklisted, False if token was invalid/already blacklisted."""
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        return False
    return True


def get_profile(user):
    """Return (profile, serializer_class) for the user's role, or (None, None)."""
    from .serializers import PROFILE_SERIALIZERS

    entry = PROFILE_SERIALIZERS.get(user.role)
    if not entry:
        return None, None
    attr, serializer_cls = entry
    return getattr(user, attr, None), serializer_cls


def update_profile(user, data, allowed_fields=None):
    """Apply profile fields for the user's role. Unknown or disallowed keys are ignored."""
    profile, serializer_cls = get_profile(user)
    if profile is None:
        return None
    if allowed_fields is not None:
        data = {k: v for k, v in data.items() if k in allowed_fields}
    if not data:
        return profile
    serializer = serializer_cls(profile, data=data, partial=True)
    if not serializer.is_valid():
        raise serializers.ValidationError({"profile": serializer.errors})
    return serializer.save()
