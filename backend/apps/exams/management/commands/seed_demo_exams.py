"""Demo question bank and exams for local development. Idempotent. Never run in production."""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.courses.models import Course, Enrollment
from apps.exams import attempts as attempt_services
from apps.exams import results as result_services
from apps.exams.models import Answer, Attempt, Exam, ExamQuestion, Option, Question, QuestionBank

User = get_user_model()

QUESTIONS = [
    ("mcq_single", "Which data structure follows last-in, first-out order?",
     ["Queue", "Stack", "Linked list", "Heap"], [1], "easy", 1,
     "A stack removes the most recently added item."),
    ("mcq_single", "What is the worst-case time complexity of binary search?",
     ["O(1)", "O(log n)", "O(n)", "O(n log n)"], [1], "easy", 1,
     "Each step halves the search range."),
    ("mcq_multi", "Which sorting algorithms have O(n log n) average time?",
     ["Merge sort", "Bubble sort", "Quick sort", "Insertion sort"], [0, 2], "medium", 2, ""),
    ("true_false", "A binary search tree always has height O(log n).",
     ["True", "False"], [1], "medium", 1, "An unbalanced BST can degrade to a linked list."),
    ("mcq_single", "Which traversal of a BST visits keys in sorted order?",
     ["Pre-order", "In-order", "Post-order", "Level-order"], [1], "easy", 1, ""),
    ("mcq_single", "Inserting at the head of a singly linked list costs:",
     ["O(1)", "O(log n)", "O(n)", "O(n^2)"], [0], "easy", 1, ""),
    ("subjective", "Explain when you would choose a hash table over a balanced BST.",
     [], [], "hard", 5, ""),
    ("true_false", "Breadth-first search uses a queue.", ["True", "False"], [0], "easy", 1, ""),
]  # fmt: skip


class Command(BaseCommand):
    help = "Create a demo question bank, a live exam and a closed graded exam (dev only)."

    @transaction.atomic
    def handle(self, *args, **options):
        course = Course.objects.filter(code="DSA101").first()
        if course is None:
            raise CommandError("Run `manage.py seed_demo_courses` first.")
        owner = course.instructor

        bank, created = QuestionBank.objects.get_or_create(
            title="DSA fundamentals",
            defaults={"owner": owner, "course": course, "description": "Core DSA questions."},
        )
        if created:
            for qtype, text, options, correct, difficulty, marks, explanation in QUESTIONS:
                q = Question.objects.create(
                    bank=bank,
                    type=qtype,
                    text=text,
                    marks=Decimal(marks),
                    negative_marks=Decimal("0.25") if qtype == "mcq_single" else Decimal("0"),
                    difficulty=difficulty,
                    explanation=explanation,
                    tags=["dsa"],
                )
                Option.objects.bulk_create(
                    [
                        Option(question=q, text=t, is_correct=i in correct, order=i)
                        for i, t in enumerate(options)
                    ]
                )

        now = timezone.now()
        questions = list(bank.questions.order_by("id"))
        live, live_created = Exam.objects.get_or_create(
            title="DSA quiz 1",
            defaults={
                "course": course,
                "created_by": owner,
                "description": "Covers stacks, queues, searching and trees. Answer every question.",
                "starts_at": now - timedelta(hours=1),
                "ends_at": now + timedelta(days=7),
                "duration_minutes": 20,
                "pass_marks": Decimal("6"),
                "status": Exam.Status.SCHEDULED,
                "reveal_answers": True,
            },
        )
        if live_created:
            self._attach(live, questions)

        closed, closed_created = Exam.objects.get_or_create(
            title="DSA diagnostic test",
            defaults={
                "course": course,
                "created_by": owner,
                "description": "Start-of-term diagnostic.",
                "starts_at": now - timedelta(days=3),
                "ends_at": now + timedelta(days=1),
                "duration_minutes": 30,
                "pass_marks": Decimal("5"),
                "status": Exam.Status.SCHEDULED,
                "reveal_answers": True,
                "shuffle_questions": False,
            },
        )
        if closed_created:
            self._attach(closed, questions)
            self._simulate_attempts(closed, course, owner)
            attempt_services.close_exam(actor=owner, exam=closed)
            Exam.objects.filter(pk=closed.pk).update(ends_at=now - timedelta(days=2))
            closed.refresh_from_db()
            result_services.release_results(actor=owner, exam=closed)

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_demo_exams: bank {'created' if created else 'exists'}, "
                f"live exam {'created' if live_created else 'exists'}, "
                f"closed exam {'created' if closed_created else 'exists'}"
            )
        )

    def _attach(self, exam, questions):
        ExamQuestion.objects.bulk_create(
            [ExamQuestion(exam=exam, question=q, order=i) for i, q in enumerate(questions)]
        )

    def _simulate_attempts(self, exam, course, grader):
        rng = random.Random(42)
        enrolled = [
            e.student
            for e in Enrollment.objects.filter(course=course, status__in=("active", "completed"))
            .select_related("student")
            .order_by("student__email")
        ]
        for skill, student in zip((0.9, 0.75, 0.55, 0.35, 0.8), enrolled, strict=False):
            attempt, _ = attempt_services.start_attempt(student=student, exam=exam)
            for eq in exam.exam_questions.select_related("question"):
                q = eq.question
                if q.type == Question.Type.SUBJECTIVE:
                    attempt_services.save_answer(
                        attempt=attempt,
                        exam_question_id=eq.pk,
                        text_answer="Hash tables give O(1) average lookups; BSTs keep order.",
                    )
                    continue
                options = list(q.options.all())
                correct = [o.pk for o in options if o.is_correct]
                wrong = [o.pk for o in options if not o.is_correct]
                pick = correct if rng.random() < skill else [rng.choice(wrong)]
                if q.type != Question.Type.MCQ_MULTI:
                    pick = pick[:1]
                attempt_services.save_answer(
                    attempt=attempt, exam_question_id=eq.pk, selected_option_ids=pick
                )
            attempt = attempt_services.submit_attempt(attempt=attempt)
            for answer in Answer.objects.filter(attempt=attempt, marks_awarded__isnull=True):
                result_services.grade_answer(
                    actor=grader,
                    answer=answer,
                    marks_awarded=Decimal(round(5 * skill)),
                    grader_feedback="Good comparison; mention worst cases too.",
                )
        Attempt.objects.filter(exam=exam).update(
            started_at=timezone.now() - timedelta(days=2, hours=1)
        )
