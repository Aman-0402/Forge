from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone
from freezegun import freeze_time

from apps.accounts.tests.factories import UserFactory
from apps.notifications import announcements
from apps.notifications.models import Announcement, Notification

URL = "/api/v1/announcements/"

pytestmark = pytest.mark.django_db


def run_command():
    out = StringIO()
    call_command("deliver_scheduled_announcements", stdout=out)
    return out.getvalue()


def post(client, **data):
    body = {"title": "Later", "body": "x", "audience": "all", **data}
    return client.post(URL, body, format="json")


def test_immediate_announcement_marked_delivered(auth_client, admin_user):
    UserFactory(role="student")
    res = post(auth_client(admin_user))
    ann = Announcement.objects.get(pk=res.data["id"])
    assert ann.delivered_at is not None
    assert Notification.objects.count() == 1


def test_scheduled_announcement_delivered_once_when_due(auth_client, admin_user):
    student = UserFactory(role="student")
    with freeze_time("2026-09-17 09:00:00") as frozen:
        publish = timezone.now() + timedelta(hours=2)
        res = post(auth_client(admin_user), published_at=publish.isoformat())
        assert res.status_code == 201
        assert "delivered 0" in run_command()
        assert not Notification.objects.exists()

        frozen.tick(timedelta(hours=2, seconds=1))
        assert "delivered 1" in run_command()
        assert "delivered 0" in run_command()

    assert list(Notification.objects.values_list("recipient_id", flat=True)) == [student.pk]
    assert Announcement.objects.get(pk=res.data["id"]).delivered_at is not None


def test_deliver_is_idempotent_even_when_called_twice(admin_user):
    UserFactory(role="student")
    ann = Announcement.objects.create(author=admin_user, title="t", body="b")
    announcements.deliver(ann)
    announcements.deliver(ann)
    ann.refresh_from_db()
    announcements.deliver(ann)
    assert Notification.objects.count() == 1


def test_expired_before_delivery_is_not_sent(admin_user):
    UserFactory(role="student")
    now = timezone.now()
    Announcement.objects.create(
        author=admin_user,
        title="missed",
        body="b",
        published_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
    )
    assert "delivered 0" in run_command()
    assert not Notification.objects.exists()


def test_editing_schedule_to_now_delivers(auth_client, admin_user):
    UserFactory(role="student")
    client = auth_client(admin_user)
    future = (timezone.now() + timedelta(days=1)).isoformat()
    ann_id = post(client, published_at=future).data["id"]
    assert not Notification.objects.exists()

    res = client.patch(
        f"{URL}{ann_id}/", {"published_at": timezone.now().isoformat()}, format="json"
    )
    assert res.status_code == 200, res.data
    assert Notification.objects.count() == 1


def test_editing_delivered_announcement_does_not_resend(auth_client, admin_user):
    UserFactory(role="student")
    client = auth_client(admin_user)
    ann_id = post(client).data["id"]
    client.patch(f"{URL}{ann_id}/", {"title": "Fixed typo"}, format="json")
    assert Notification.objects.count() == 1


def test_serializer_exposes_delivered_at_read_only(auth_client, admin_user):
    res = post(auth_client(admin_user), delivered_at="2020-01-01T00:00:00Z")
    assert res.data["delivered_at"] != "2020-01-01T00:00:00Z"
