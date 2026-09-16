import pytest

from apps.core.models import MarketingStat

URL = "/api/v1/marketing-stats/"

pytestmark = pytest.mark.django_db


def make(**kw):
    defaults = {"order": 0, "value": "95", "suffix": "%", "description": "consistent practice"}
    defaults.update(kw)
    return MarketingStat.objects.create(**defaults)


def test_public_lists_stats_in_order(api_client):
    # The core.0002 data migration seeds 3 default stats so the public site never
    # ships empty; clear them here to test ordering on a known set.
    MarketingStat.objects.all().delete()
    make(order=2, value="85", description="third")
    make(order=0, value="95", description="first")
    make(order=1, value="5000", description="second")

    res = api_client.get(URL)
    assert res.status_code == 200
    assert [s["description"] for s in res.data] == ["first", "second", "third"]


def test_admin_can_create_update_and_delete(auth_client, admin_user):
    admin = auth_client(admin_user)
    created = admin.post(
        URL,
        {"order": 0, "value": "95", "suffix": "%", "description": "learn more consistently"},
        format="json",
    )
    assert created.status_code == 201, created.data
    stat_id = created.data["id"]

    updated = admin.patch(f"{URL}{stat_id}/", {"value": "97"}, format="json")
    assert updated.status_code == 200 and updated.data["value"] == "97"

    assert admin.delete(f"{URL}{stat_id}/").status_code == 204
    assert not MarketingStat.objects.filter(pk=stat_id).exists()


def test_non_admin_can_read_but_not_write(auth_client, student_user):
    student = auth_client(student_user)
    assert student.get(URL).status_code == 200
    assert student.post(URL, {"order": 0, "value": "1"}, format="json").status_code == 403


def test_anonymous_can_read_but_not_write(api_client):
    assert api_client.get(URL).status_code == 200
    assert api_client.post(URL, {"order": 0, "value": "1"}, format="json").status_code in (401, 403)


def test_default_stats_are_seeded_so_the_public_site_is_never_empty(api_client):
    # core.migrations.0002_seed_marketing_stats
    assert MarketingStat.objects.count() == 3
    assert api_client.get(URL).status_code == 200
