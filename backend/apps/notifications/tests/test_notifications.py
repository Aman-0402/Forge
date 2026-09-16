import pytest
from django.core import mail

from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification
from apps.notifications.services import notify

URL = "/api/v1/notifications/"

pytestmark = pytest.mark.django_db


def test_notify_creates_one_row_per_user_without_email():
    users = [UserFactory(), UserFactory()]
    created = notify(users, "Hello", "Body", kind="info", link="/x")
    assert len(created) == 2
    assert Notification.objects.filter(title="Hello", link="/x").count() == 2
    assert mail.outbox == []


def test_notify_with_email_sends_to_active_users_with_email():
    active = UserFactory(email="a@forge.test")
    inactive = UserFactory(email="b@forge.test", is_active=False)
    notify([active, inactive], "Exam scheduled", "Tomorrow 10:00", kind="exam", email=True)
    assert Notification.objects.count() == 2
    assert [m.to for m in mail.outbox] == [["a@forge.test"]]
    assert mail.outbox[0].subject == "Exam scheduled"


def test_notify_accepts_queryset_and_skips_duplicates():
    UserFactory.create_batch(3, role="student")
    from django.contrib.auth import get_user_model

    qs = get_user_model().objects.filter(role="student")
    assert len(notify(qs, "t", "b")) == 3


def test_list_requires_auth(api_client):
    assert api_client.get(URL).status_code == 401


def test_user_sees_only_own_notifications_newest_first(auth_client, student_user):
    other = UserFactory()
    notify([student_user], "first", "")
    notify([student_user], "second", "")
    notify([other], "not mine", "")
    res = auth_client(student_user).get(URL)
    assert [n["title"] for n in res.data["results"]] == ["second", "first"]


def test_unread_filter_and_count(auth_client, student_user):
    a, b = notify([student_user], "a", "")[0], notify([student_user], "b", "")[0]
    a.is_read = True
    a.save()
    client = auth_client(student_user)
    assert [n["title"] for n in client.get(URL, {"unread": "true"}).data["results"]] == ["b"]
    assert client.get(f"{URL}unread-count/").data == {"count": 1}
    assert b.pk


def test_mark_read(auth_client, student_user):
    n = notify([student_user], "a", "")[0]
    res = auth_client(student_user).post(f"{URL}{n.pk}/read/")
    assert res.status_code == 200
    n.refresh_from_db()
    assert n.is_read and n.read_at is not None


def test_cannot_mark_someone_elses_notification(auth_client, student_user):
    other = UserFactory()
    n = notify([other], "a", "")[0]
    assert auth_client(student_user).post(f"{URL}{n.pk}/read/").status_code == 404


def test_read_all_marks_only_own(auth_client, student_user):
    other = UserFactory()
    notify([student_user], "a", "")
    notify([student_user], "b", "")
    notify([other], "c", "")
    res = auth_client(student_user).post(f"{URL}read-all/")
    assert res.status_code == 200
    assert res.data == {"updated": 2}
    assert Notification.objects.filter(recipient=other, is_read=False).count() == 1


def test_notifications_are_not_creatable_via_api(auth_client, admin_user):
    assert auth_client(admin_user).post(URL, {"title": "x"}, format="json").status_code == 405
