import pytest
from django.core import mail

from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import ContactMessage, Notification

URL = "/api/v1/contact/"

pytestmark = pytest.mark.django_db


def test_public_visitor_can_send_a_message(api_client, admin_user):
    other_admin = UserFactory(role="admin")
    UserFactory(role="faculty")  # not notified: not an admin

    res = api_client.post(
        URL,
        {"name": "Priya Rao", "email": "priya@example.com", "message": "How do I enrol?"},
        format="json",
    )

    assert res.status_code == 201, res.data
    saved = ContactMessage.objects.get()
    assert saved.name == "Priya Rao" and saved.email == "priya@example.com"

    notified = set(
        Notification.objects.filter(kind=Notification.Kind.INFO).values_list(
            "recipient_id", flat=True
        )
    )
    assert notified == {admin_user.pk, other_admin.pk}
    assert mail.outbox and "priya@example.com" in mail.outbox[0].body


@pytest.mark.parametrize(
    "body",
    [
        {"email": "a@b.com", "message": "hi"},
        {"name": "A", "message": "hi"},
        {"name": "A", "email": "not-an-email", "message": "hi"},
        {"name": "A", "email": "a@b.com", "message": ""},
    ],
)
def test_rejects_invalid_input(api_client, body):
    assert api_client.post(URL, body, format="json").status_code == 400


def test_no_admins_still_saves_the_message(api_client):
    res = api_client.post(URL, {"name": "A", "email": "a@b.com", "message": "hello"}, format="json")
    assert res.status_code == 201
    assert ContactMessage.objects.count() == 1
