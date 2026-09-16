"""Create demo courses for local development. Idempotent. Never run in production."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.courses.models import (
    Assignment,
    Category,
    Chapter,
    ContentItem,
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    Module,
)
from apps.courses.progress import recompute_enrollment

User = get_user_model()

COURSES = [
    {
        "code": "DSA101",
        "title": "Data Structures and Algorithms",
        "level": "beginner",
        "category": "Computer Science",
        "status": "published",
        "mode": "open",
        "description": (
            "Arrays, linked lists, stacks, queues, trees and graphs, with the searching and "
            "sorting techniques that use them. Each module ends with practice problems."
        ),
        "modules": {
            "Foundations": {
                "Complexity": [
                    "Why measure algorithms",
                    "Big-O notation",
                    "Best, average and worst case",
                ],
                "Arrays": ["Static and dynamic arrays", "Two-pointer technique"],
            },
            "Linear structures": {
                "Linked lists": ["Singly linked lists", "Doubly linked lists"],
                "Stacks and queues": ["Stack operations", "Queues and deques"],
            },
            "Trees": {
                "Binary trees": ["Traversals", "Binary search trees", "Balancing basics"],
            },
        },
        "assignments": [("Implement a stack", 3, 20), ("Big-O worksheet", 7, 10)],
    },
    {
        "code": "PY110",
        "title": "Python Programming",
        "level": "beginner",
        "category": "Programming",
        "status": "published",
        "mode": "open",
        "description": "Write clear Python: data types, control flow, functions, files and modules.",
        "modules": {
            "Getting started": {
                "Setup": ["Installing Python", "Your first script"],
                "Basics": ["Variables and types", "Conditionals", "Loops"],
            },
            "Functions": {"Writing functions": ["Parameters and returns", "Scope"]},
        },
        "assignments": [("Temperature converter", 5, 10)],
    },
    {
        "code": "DB220",
        "title": "Database Systems",
        "level": "intermediate",
        "category": "Computer Science",
        "status": "published",
        "mode": "manual",
        "description": "Relational modelling, SQL, normalisation, indexing and transactions.",
        "modules": {
            "Relational model": {
                "Tables and keys": ["Entities and relations", "Primary and foreign keys"]
            },
            "SQL": {"Queries": ["SELECT and WHERE", "Joins", "Aggregates"]},
        },
        "assignments": [],
    },
    {
        "code": "ML300",
        "title": "Machine Learning Fundamentals",
        "level": "advanced",
        "category": "Data Science",
        "status": "draft",
        "mode": "manual",
        "description": "Supervised learning, evaluation and model selection. Draft in progress.",
        "modules": {"Introduction": {"Overview": ["What is learning", "Train and test splits"]}},
        "assignments": [],
    },
]


class Command(BaseCommand):
    help = "Create demo courses, lessons, enrollments and assignments (idempotent, dev only)."

    @transaction.atomic
    def handle(self, *args, **options):
        instructor = User.objects.filter(email="faculty1@forge.local").first()
        if instructor is None:
            raise CommandError("Run `manage.py seed_dev` first.")
        admin = User.objects.filter(role="admin").first()
        students = list(User.objects.filter(role="student", is_active=True).order_by("email")[:6])

        created = 0
        for spec in COURSES:
            if Course.objects.filter(code=spec["code"]).exists():
                continue
            created += 1
            course = self._course(spec, instructor, admin)
            lessons = self._structure(course, spec["modules"])
            for title, days, marks in spec["assignments"]:
                Assignment.objects.create(
                    course=course,
                    title=title,
                    description=f"Complete '{title}' and upload your work.",
                    due_at=timezone.now() + timedelta(days=days),
                    max_marks=marks,
                    allow_late=True,
                    created_by=instructor,
                )
            if course.status == Course.Status.PUBLISHED:
                self._enroll(course, students, lessons)

        self.stdout.write(self.style.SUCCESS(f"seed_demo_courses: {created} courses created"))

    def _course(self, spec, instructor, admin):
        category, _ = Category.objects.get_or_create(name=spec["category"])
        course = Course.objects.create(
            code=spec["code"],
            title=spec["title"],
            description=spec["description"],
            level=spec["level"],
            instructor=instructor,
            status=spec["status"],
            enrollment_mode=spec["mode"],
            approved_by=admin if spec["status"] == "published" else None,
            approved_at=timezone.now() if spec["status"] == "published" else None,
        )
        course.categories.add(category)
        return course

    def _structure(self, course, modules):
        lessons = []
        for m_index, (module_title, chapters) in enumerate(modules.items()):
            module = Module.objects.create(course=course, title=module_title, order=m_index)
            for c_index, (chapter_title, lesson_titles) in enumerate(chapters.items()):
                chapter = Chapter.objects.create(module=module, title=chapter_title, order=c_index)
                for l_index, lesson_title in enumerate(lesson_titles):
                    lesson = Lesson.objects.create(
                        chapter=chapter,
                        title=lesson_title,
                        order=l_index,
                        duration_minutes=10 + (l_index * 5),
                        is_preview=(m_index == 0 and c_index == 0 and l_index == 0),
                        summary=f"{lesson_title} in {chapter_title.lower()}.",
                    )
                    ContentItem.objects.create(
                        lesson=lesson,
                        kind=ContentItem.Kind.TEXT,
                        title="Reading",
                        text=(
                            f"{lesson_title}\n\nThis reading introduces the idea, walks through "
                            "an example step by step, and ends with two short exercises to try "
                            "before the next lesson."
                        ),
                    )
                    lessons.append(lesson)
        return lessons

    def _enroll(self, course, students, lessons):
        for index, student in enumerate(students):
            enrollment, _ = Enrollment.objects.get_or_create(
                course=course, student=student, defaults={"source": Enrollment.Source.MANUAL}
            )
            done = lessons[: (len(lessons) * index) // max(1, len(students) - 1)]
            for lesson in done:
                LessonProgress.objects.get_or_create(
                    enrollment=enrollment, lesson=lesson, defaults={"completed_at": timezone.now()}
                )
            recompute_enrollment(enrollment, total=len(lessons))
