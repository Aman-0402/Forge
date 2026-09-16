import factory

from apps.accounts.tests.factories import UserFactory
from apps.coding.models import Language, Problem, TestCase


class LanguageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Language
        django_get_or_create = ("judge0_id",)

    name = "Python"
    slug = factory.Sequence(lambda n: f"python-{n}")
    judge0_id = 71
    version = "3.8.1"
    editor_mode = "python"


class ProblemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Problem

    title = factory.Sequence(lambda n: f"Problem {n}")
    statement = "Read two integers and print their sum."
    created_by = factory.SubFactory(UserFactory, role="faculty")
    status = Problem.Status.PUBLISHED


def add_cases(problem, samples=((("1 2", "3"),)), hidden=(("10 20", "30"), ("-1 1", "0"))):
    order = 0
    for inp, out in samples:
        TestCase.objects.create(
            problem=problem,
            input=inp,
            expected_output=out,
            is_sample=True,
            is_hidden=False,
            order=order,
        )
        order += 1
    for inp, out in hidden:
        TestCase.objects.create(
            problem=problem, input=inp, expected_output=out, is_hidden=True, order=order
        )
        order += 1
    return problem
