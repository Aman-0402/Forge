import pytest
from django.core.management import call_command

from apps.courses.models import Assignment, Course, Enrollment, Lesson

pytestmark = pytest.mark.django_db


def test_seed_demo_courses_is_idempotent():
    call_command("seed_dev")
    call_command("seed_demo_courses")
    call_command("seed_demo_courses")

    assert Course.objects.filter(status="published").count() == 3
    assert Course.objects.filter(status="draft").count() == 1
    assert Lesson.objects.count() > 10
    assert Assignment.objects.count() >= 2
    course = Course.objects.get(code="DSA101")
    assert course.instructor.email == "faculty1@forge.local"
    assert Enrollment.objects.filter(course=course).count() >= 3
    progressed = Enrollment.objects.filter(progress_percent__gt=0).count()
    assert progressed >= 1
