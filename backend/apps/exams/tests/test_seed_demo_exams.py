import pytest
from django.core.management import call_command

from apps.exams.models import Attempt, Exam, QuestionBank

pytestmark = pytest.mark.django_db


def test_seed_demo_exams_is_idempotent():
    call_command("seed_dev")
    call_command("seed_demo_courses")
    call_command("seed_demo_exams")
    call_command("seed_demo_exams")

    assert QuestionBank.objects.filter(title="DSA fundamentals").count() == 1
    live = Exam.objects.get(title="DSA quiz 1")
    assert live.phase == "live" and live.exam_questions.count() >= 6
    closed = Exam.objects.get(title="DSA diagnostic test")
    assert closed.status == "closed" and closed.results_released_at is not None
    assert Attempt.objects.filter(exam=closed, status="graded").count() >= 3
    assert not Attempt.objects.filter(exam=live).exists()
