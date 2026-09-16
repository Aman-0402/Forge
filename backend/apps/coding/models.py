from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class Language(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=40, unique=True)
    judge0_id = models.PositiveIntegerField(unique=True)
    version = models.CharField(max_length=60, blank=True)
    editor_mode = models.CharField(
        max_length=30, default="plaintext", help_text="Code editor language id, e.g. python, cpp."
    )
    default_template = models.TextField(blank=True)
    is_enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} {self.version}".strip()


class Problem(TimeStampedModel):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    statement = models.TextField()
    input_format = models.TextField(blank=True)
    output_format = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=6, choices=Difficulty.choices, default=Difficulty.EASY, db_index=True
    )
    tags = models.JSONField(default=list, blank=True)
    time_limit_seconds = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("2"),
        validators=[MinValueValidator(Decimal("0.1")), MaxValueValidator(Decimal("15"))],
    )
    memory_limit_kb = models.PositiveIntegerField(
        default=128000, validators=[MinValueValidator(2048), MaxValueValidator(512000)]
    )
    max_score = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])
    allow_partial = models.BooleanField(default=True)
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="problems",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="problems_created"
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    allowed_languages = models.ManyToManyField(Language, blank=True, related_name="+")
    visible_from = models.DateTimeField(null=True, blank=True)
    visible_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            from apps.courses.models import unique_slug

            self.slug = unique_slug(Problem, self.title, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def languages(self):
        chosen = self.allowed_languages.filter(is_enabled=True)
        return chosen if chosen.exists() else Language.objects.filter(is_enabled=True)


class TestCase(models.Model):
    __test__ = False  # not a pytest test class

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="test_cases")
    input = models.TextField(blank=True)
    expected_output = models.TextField(blank=True)
    is_sample = models.BooleanField(default=False, help_text="Shown in the problem statement.")
    is_hidden = models.BooleanField(default=True, help_text="Input and output never shown.")
    weight = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    order = models.PositiveIntegerField(default=0)
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["order", "id"]


class CodeSubmission(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        ERROR = "error", "Error"

    class Verdict(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        PARTIAL = "partial", "Partially correct"
        WRONG_ANSWER = "wrong_answer", "Wrong answer"
        TIME_LIMIT = "time_limit", "Time limit exceeded"
        MEMORY_LIMIT = "memory_limit", "Memory limit exceeded"
        RUNTIME_ERROR = "runtime_error", "Runtime error"
        COMPILE_ERROR = "compile_error", "Compilation error"
        INTERNAL_ERROR = "internal_error", "Judge error"

    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="code_submissions"
    )
    language = models.ForeignKey(Language, on_delete=models.PROTECT, related_name="+")
    source_code = models.TextField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    verdict = models.CharField(max_length=16, choices=Verdict.choices, blank=True, db_index=True)
    score = models.PositiveIntegerField(default=0)
    passed_count = models.PositiveIntegerField(default=0)
    total_count = models.PositiveIntegerField(default=0)
    max_time_seconds = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    max_memory_kb = models.PositiveIntegerField(null=True, blank=True)
    compile_output = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    judged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]
        indexes = [models.Index(fields=["problem", "student", "submitted_at"])]

    def __str__(self):
        return f"{self.student_id} on {self.problem_id}: {self.verdict or self.status}"


class TestCaseResult(models.Model):
    __test__ = False

    submission = models.ForeignKey(CodeSubmission, on_delete=models.CASCADE, related_name="results")
    test_case = models.ForeignKey(TestCase, on_delete=models.SET_NULL, null=True, related_name="+")
    judge0_token = models.CharField(max_length=64, blank=True)
    verdict = models.CharField(max_length=16, choices=CodeSubmission.Verdict.choices)
    passed = models.BooleanField(default=False)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    time_seconds = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    memory_kb = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
