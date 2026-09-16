import pytest
from django.core.management import call_command

from apps.coding.models import Language, Problem

pytestmark = pytest.mark.django_db


def test_seed_demo_problems_is_idempotent():
    call_command("seed_dev")
    call_command("seed_demo_courses")
    call_command("seed_demo_problems")
    call_command("seed_demo_problems")

    assert Language.objects.count() == 5
    published = Problem.objects.filter(status="published")
    assert published.count() == 3
    two_sum = Problem.objects.get(title="Sum of two numbers")
    assert two_sum.test_cases.filter(is_sample=True).exists()
    assert two_sum.test_cases.filter(is_hidden=True).count() >= 3
    assert Problem.objects.filter(status="draft").count() == 1
