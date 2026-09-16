from datetime import timedelta

import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.exams.models import Exam, ExamQuestion, Option, Question, QuestionBank


class QuestionBankFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = QuestionBank

    title = factory.Sequence(lambda n: f"Bank {n}")
    owner = factory.SubFactory(UserFactory, role="faculty")


class QuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Question

    bank = factory.SubFactory(QuestionBankFactory)
    type = Question.Type.MCQ_SINGLE
    text = factory.Sequence(lambda n: f"Question {n}?")
    marks = 2
    negative_marks = 0


def mcq(bank=None, correct=(0,), n_options=4, type_=Question.Type.MCQ_SINGLE, **kwargs):
    """Objective question with options; ``correct`` holds indexes of correct options."""
    question = QuestionFactory(bank=bank or QuestionBankFactory(), type=type_, **kwargs)
    for i in range(n_options):
        Option.objects.create(
            question=question, text=f"Option {i}", is_correct=i in correct, order=i
        )
    return question


def true_false(bank=None, answer=True, **kwargs):
    question = QuestionFactory(
        bank=bank or QuestionBankFactory(), type=Question.Type.TRUE_FALSE, **kwargs
    )
    Option.objects.create(question=question, text="True", is_correct=answer, order=0)
    Option.objects.create(question=question, text="False", is_correct=not answer, order=1)
    return question


def subjective(bank=None, **kwargs):
    return QuestionFactory(
        bank=bank or QuestionBankFactory(), type=Question.Type.SUBJECTIVE, **kwargs
    )


class ExamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Exam

    title = factory.Sequence(lambda n: f"Exam {n}")
    created_by = factory.SubFactory(UserFactory, role="faculty")
    starts_at = factory.LazyFunction(lambda: timezone.now() - timedelta(minutes=5))
    ends_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=2))
    duration_minutes = 30
    status = Exam.Status.SCHEDULED
    shuffle_questions = False
    shuffle_options = False


def add_questions(exam, *questions):
    for i, q in enumerate(questions):
        ExamQuestion.objects.create(exam=exam, question=q, order=i)
    return exam
