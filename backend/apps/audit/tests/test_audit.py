from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.audit.services import log_action

URL = "/api/v1/audit-logs/"

pytestmark = pytest.mark.django_db


def test_log_action_records_actor_target_metadata_and_ip(admin_user, student_user):
    request = RequestFactory().post("/x", REMOTE_ADDR="10.1.2.3")
    entry = log_action(
        admin_user, "user.update", target=student_user, metadata={"a": 1}, request=request
    )
    entry.refresh_from_db()
    assert entry.actor == admin_user
    assert entry.action == "user.update"
    assert entry.target_type == "accounts.user"
    assert entry.target_id == str(student_user.pk)
    assert entry.metadata == {"a": 1}
    assert entry.ip == "10.1.2.3"


def test_log_action_prefers_x_forwarded_for(admin_user):
    request = RequestFactory().post(
        "/x", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="203.0.113.9, 10.0.0.1"
    )
    assert log_action(admin_user, "x", request=request).ip == "203.0.113.9"


def test_log_action_allows_system_actor_without_target():
    entry = log_action(None, "system.sweep")
    assert entry.actor is None and entry.target_type == "" and entry.metadata == {}


def test_audit_logs_admin_only(api_client, auth_client, admin_user, faculty_user, student_user):
    assert api_client.get(URL).status_code == 401
    assert auth_client(faculty_user).get(URL).status_code == 403
    assert auth_client(student_user).get(URL).status_code == 403
    assert auth_client(admin_user).get(URL).status_code == 200


def test_audit_logs_list_newest_first_with_actor_email(auth_client, admin_user):
    log_action(admin_user, "first")
    log_action(admin_user, "second")
    res = auth_client(admin_user).get(URL)
    assert [r["action"] for r in res.data["results"]] == ["second", "first"]
    assert res.data["results"][0]["actor_email"] == admin_user.email


def test_audit_logs_filters(auth_client, admin_user):
    other = UserFactory(role="faculty")
    log_action(admin_user, "user.create")
    log_action(other, "announcement.create")
    old = log_action(admin_user, "user.update")
    AuditLog.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=10))
    client = auth_client(admin_user)

    by_action = client.get(URL, {"action": "announcement.create"}).data["results"]
    assert [r["action"] for r in by_action] == ["announcement.create"]

    by_actor = client.get(URL, {"actor": other.pk}).data["results"]
    assert [r["action"] for r in by_actor] == ["announcement.create"]

    since = (timezone.now() - timedelta(days=1)).isoformat()
    recent = client.get(URL, {"created_after": since}).data["results"]
    assert "user.update" not in [r["action"] for r in recent]


def test_audit_logs_are_read_only(auth_client, admin_user):
    entry = log_action(admin_user, "x")
    client = auth_client(admin_user)
    assert client.post(URL, {"action": "fake"}, format="json").status_code == 405
    assert client.delete(f"{URL}{entry.pk}/").status_code == 405
