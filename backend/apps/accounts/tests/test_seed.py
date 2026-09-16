import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

User = get_user_model()


@pytest.mark.django_db
def test_seed_dev_creates_users_and_is_idempotent():
    call_command("seed_dev")
    call_command("seed_dev")
    assert User.objects.filter(role="admin").count() == 1
    assert User.objects.filter(role="faculty").count() == 2
    assert User.objects.filter(role="student").count() == 5
    admin = User.objects.get(email="admin@forge.local")
    assert admin.is_superuser and admin.check_password("Admin@12345")
