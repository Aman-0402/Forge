import pytest
from rest_framework.test import APIClient

PASSWORD = "Str0ng-Pass!word"


@pytest.fixture(autouse=True)
def _isolated_media(settings, tmp_path):
    """Uploaded files in tests go to a temp dir, never to backend/media."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def password():
    return PASSWORD


@pytest.fixture
def admin_user(db):
    from apps.accounts.tests.factories import UserFactory

    return UserFactory(role="admin", email="admin@forge.test")


@pytest.fixture
def faculty_user(db):
    from apps.accounts.tests.factories import UserFactory

    return UserFactory(role="faculty", email="faculty@forge.test")


@pytest.fixture
def student_user(db):
    from apps.accounts.tests.factories import UserFactory

    return UserFactory(role="student", email="student@forge.test")


@pytest.fixture
def auth_client():
    """Return a function that builds an APIClient authenticated as the given user."""

    def _make(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _make
