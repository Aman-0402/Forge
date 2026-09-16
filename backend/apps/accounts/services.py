from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework_simplejwt.exceptions import TokenError
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


def change_password(user, new_password):
    user.set_password(new_password)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "updated_at"])


def blacklist_refresh_token(raw_token):
    """Return True if blacklisted, False if token was invalid/already blacklisted."""
    try:
        RefreshToken(raw_token).blacklist()
    except TokenError:
        return False
    return True
