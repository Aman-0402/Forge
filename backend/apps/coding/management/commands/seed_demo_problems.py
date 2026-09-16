"""Demo coding problems for local development. Idempotent. Never run in production."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.coding.models import Problem, TestCase
from apps.courses.models import Course

User = get_user_model()

PROBLEMS = [
    {
        "title": "Sum of two numbers",
        "difficulty": "easy",
        "tags": ["math", "warm-up"],
        "status": "published",
        "statement": "Read two integers a and b and print their sum.",
        "input_format": "One line with two integers a and b separated by a space.",
        "output_format": "Print a + b.",
        "constraints": "-10^9 ≤ a, b ≤ 10^9",
        "samples": [("2 3", "5", "2 + 3 = 5")],
        "hidden": [("0 0", "0"), ("-7 7", "0"), ("1000000000 1000000000", "2000000000")],
    },
    {
        "title": "Reverse a string",
        "difficulty": "easy",
        "tags": ["strings"],
        "status": "published",
        "statement": "Read a word and print it reversed.",
        "input_format": "A single word of lowercase letters.",
        "output_format": "The word reversed.",
        "constraints": "1 ≤ length ≤ 10^5",
        "samples": [("forge", "egrof", "")],
        "hidden": [("a", "a"), ("racecar", "racecar"), ("abcdef", "fedcba")],
    },
    {
        "title": "Maximum subarray sum",
        "difficulty": "medium",
        "tags": ["arrays", "dynamic programming"],
        "status": "published",
        "course_code": "DSA101",
        "statement": (
            "Given an array of n integers, find the largest sum of any non-empty "
            "contiguous subarray."
        ),
        "input_format": "First line n. Second line n integers.",
        "output_format": "The maximum subarray sum.",
        "constraints": "1 ≤ n ≤ 2·10^5, |a_i| ≤ 10^4",
        "samples": [("9\n-2 1 -3 4 -1 2 1 -5 4", "6", "The subarray 4 -1 2 1 sums to 6.")],
        "hidden": [("1\n-5", "-5"), ("5\n1 2 3 4 5", "15"), ("6\n-1 -2 10 -1 -2 3", "10")],
    },
    {
        "title": "Balanced brackets",
        "difficulty": "medium",
        "tags": ["stacks"],
        "status": "draft",
        "statement": "Print YES if the bracket string is balanced, otherwise NO.",
        "input_format": "A string of ()[]{} characters.",
        "output_format": "YES or NO.",
        "constraints": "1 ≤ length ≤ 10^5",
        "samples": [("([]{})", "YES", "")],
        "hidden": [("(]", "NO"), ("((", "NO")],
    },
]


class Command(BaseCommand):
    help = "Create demo coding problems with test cases (idempotent, dev only)."

    @transaction.atomic
    def handle(self, *args, **options):
        author = User.objects.filter(email="faculty1@forge.local").first()
        if author is None:
            raise CommandError("Run `manage.py seed_dev` first.")
        call_command("seed_languages", stdout=self.stdout)

        created = 0
        for spec in PROBLEMS:
            if Problem.objects.filter(title=spec["title"]).exists():
                continue
            course = Course.objects.filter(code=spec.get("course_code", "")).first()
            problem = Problem.objects.create(
                title=spec["title"],
                difficulty=spec["difficulty"],
                tags=spec["tags"],
                status=spec["status"],
                statement=spec["statement"],
                input_format=spec["input_format"],
                output_format=spec["output_format"],
                constraints=spec["constraints"],
                course=course,
                created_by=author,
            )
            order = 0
            for inp, out, explanation in spec["samples"]:
                TestCase.objects.create(
                    problem=problem,
                    input=inp,
                    expected_output=out,
                    explanation=explanation,
                    is_sample=True,
                    is_hidden=False,
                    order=order,
                )
                order += 1
            for inp, out in spec["hidden"]:
                TestCase.objects.create(
                    problem=problem, input=inp, expected_output=out, is_hidden=True, order=order
                )
                order += 1
            created += 1
        self.stdout.write(self.style.SUCCESS(f"seed_demo_problems: {created} problems created"))
