"""Admin user-management services: create, update, deactivate, reset, bulk import."""

import csv
import io
import secrets
import string

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_action
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Department
from .services import revoke_tokens, update_profile

User = get_user_model()

BULK_MAX_BYTES = 1_000_000
BULK_MAX_ROWS = 1000
BULK_REQUIRED_HEADERS = {"email", "role"}
BULK_PROFILE_COLUMNS = ("roll_number", "batch", "year", "employee_id", "designation")


def generate_temp_password():
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"{core}#{secrets.randbelow(90) + 10}"


def _notify_credentials(user, temp_password, *, reset):
    if reset:
        title = "Your Forge LMS password was reset"
        body = "An administrator reset your password."
    else:
        title = "Your Forge LMS account is ready"
        body = f"An account was created for {user.email} with role '{user.role}'."
    if temp_password:
        body += (
            f"\n\nTemporary password: {temp_password}\n"
            "You will be asked to change it after you sign in."
        )
    notify([user], title, body, kind=Notification.Kind.ACCOUNT, email=True)


@transaction.atomic
def admin_create_user(*, actor, data, request=None):
    """Create a user. Returns ``(user, temp_password)``; temp is None if a password was given."""
    data = dict(data)
    profile = data.pop("profile", None)
    password = data.pop("password", "") or None
    email = data.pop("email")
    temp_password = None
    if not password:
        temp_password = password = generate_temp_password()
    user = User.objects.create_user(
        email=email,
        password=password,
        must_change_password=temp_password is not None,
        **data,
    )
    if profile:
        update_profile(user, profile)
    log_action(actor, "user.create", target=user, metadata={"role": user.role}, request=request)
    _notify_credentials(user, temp_password, reset=False)
    return user, temp_password


@transaction.atomic
def admin_update_user(*, actor, user, data, request=None):
    data = dict(data)
    if user.pk == actor.pk:
        if "role" in data and data["role"] != user.role:
            raise ValidationError({"role": ["You cannot change your own role."]})
        if data.get("is_active") is False:
            raise ValidationError({"is_active": ["You cannot deactivate your own account."]})

    profile = data.pop("profile", None)
    password = data.pop("password", "") or None
    changed = sorted(
        [*data, *(["profile"] if profile else []), *(["password"] if password else [])]
    )
    was_active = user.is_active

    for field, value in data.items():
        setattr(user, field, value)
    if password:
        user.set_password(password)
    user.save()
    if profile:
        update_profile(user, profile)
    if password or (was_active and not user.is_active):
        revoke_tokens(user)

    log_action(actor, "user.update", target=user, metadata={"fields": changed}, request=request)
    return user


@transaction.atomic
def deactivate_user(*, actor, user, request=None):
    if user.pk == actor.pk:
        raise ValidationError({"detail": ["You cannot deactivate your own account."]})
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    revoke_tokens(user)
    log_action(actor, "user.deactivate", target=user, request=request)
    return user


@transaction.atomic
def reset_password(*, actor, user, request=None):
    temp_password = generate_temp_password()
    user.set_password(temp_password)
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password", "updated_at"])
    revoke_tokens(user)
    log_action(actor, "user.reset_password", target=user, request=request)
    _notify_credentials(user, temp_password, reset=True)
    return temp_password


def _read_csv(file):
    if file is None:
        raise ValidationError({"file": ["This field is required."]})
    if file.size > BULK_MAX_BYTES:
        raise ValidationError({"file": ["File too large (max 1 MB)."]})
    try:
        text = file.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError({"file": ["File must be a UTF-8 encoded CSV."]}) from exc
    reader = csv.DictReader(io.StringIO(text))
    headers = {(h or "").strip().lower() for h in (reader.fieldnames or [])}
    missing = BULK_REQUIRED_HEADERS - headers
    if missing:
        raise ValidationError(
            {"file": [f"Missing required columns: {', '.join(sorted(missing))}."]}
        )
    return reader


def bulk_import_users(*, actor, file, request=None):
    """Create users from CSV. Each row succeeds or fails on its own.

    Columns: email, role (required); first_name, last_name, phone, department_code,
    roll_number, batch, year, employee_id, designation (optional).
    Row numbers in the result count the header as row 1.
    """
    from .serializers import AdminUserSerializer

    reader = _read_csv(file)
    departments = {d.code.upper(): d.pk for d in Department.objects.all()}
    created, errors = [], []

    for row_number, raw in enumerate(reader, start=2):
        if row_number - 1 > BULK_MAX_ROWS:
            errors.append({"row": row_number, "errors": {"file": [f"Max {BULK_MAX_ROWS} rows."]}})
            break
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(row.values()):
            continue

        payload = {
            "email": row.get("email", ""),
            "first_name": row.get("first_name", ""),
            "last_name": row.get("last_name", ""),
            "phone": row.get("phone", ""),
            "role": row.get("role", "").lower(),
        }
        code = row.get("department_code", "")
        if code:
            if code.upper() not in departments:
                errors.append(
                    {"row": row_number, "errors": {"department_code": [f"Unknown '{code}'."]}}
                )
                continue
            payload["department"] = departments[code.upper()]
        profile = {k: row[k] for k in BULK_PROFILE_COLUMNS if row.get(k)}
        if profile:
            payload["profile"] = profile

        serializer = AdminUserSerializer(data=payload)
        if not serializer.is_valid():
            errors.append({"row": row_number, "errors": serializer.errors})
            continue
        try:
            with transaction.atomic():
                user, temp = admin_create_user(
                    actor=actor, data=serializer.validated_data, request=request
                )
        except ValidationError as exc:
            errors.append({"row": row_number, "errors": exc.detail})
            continue
        created.append(
            {"row": row_number, "email": user.email, "role": user.role, "temp_password": temp}
        )

    log_action(
        actor,
        "user.bulk_import",
        metadata={"created": len(created), "failed": len(errors)},
        request=request,
    )
    return {"created": created, "errors": errors}
