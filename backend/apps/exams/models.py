from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel

MARKS = {"max_digits": 6, "decimal_places": 2}


class QuestionBank(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="question_banks"
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="question_banks",
    )
    is_shared = models.BooleanField(default=False)

    class Meta:
        ordering = ["title", "id"]

    def __str__(self):
        return self.title


class Question(TimeStampedModel):
    class Type(models.TextChoices):
        MCQ_SINGLE = "mcq_single", "Multiple choice (one answer)"
        MCQ_MULTI = "mcq_multi", "Multiple choice (several answers)"
        TRUE_FALSE = "true_false", "True / false"
        SUBJECTIVE = "subjective", "Written answer"

    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    OBJECTIVE_TYPES = (Type.MCQ_SINGLE, Type.MCQ_MULTI, Type.TRUE_FALSE)

    bank = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name="questions")
    type = models.CharField(max_length=12, choices=Type.choices)
    text = models.TextField()
    marks = models.DecimalField(**MARKS, validators=[MinValueValidator(Decimal("0"))])
    negative_marks = models.DecimalField(
        **MARKS, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))]
    )
    difficulty = models.CharField(
        max_length=6, choices=Difficulty.choices, default=Difficulty.MEDIUM, db_index=True
    )
    explanation = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.text[:60]

    @property
    def is_objective(self):
        return self.type in self.OBJECTIVE_TYPES


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:60]


class Exam(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    course = models.ForeignKey(
        "courses.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="exams"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exams_created"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    pass_marks = models.DecimalField(**MARKS, null=True, blank=True)
    shuffle_questions = models.BooleanField(default=True)
    shuffle_options = models.BooleanField(default=True)
    max_attempts = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    show_result_immediately = models.BooleanField(default=False)
    reveal_answers = models.BooleanField(default=False)
    results_released_at = models.DateTimeField(null=True, blank=True)
    integrity_tracking = models.BooleanField(default=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    allowed_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="exams_allowed"
    )
    questions = models.ManyToManyField(Question, through="ExamQuestion", related_name="exams")

    class Meta:
        ordering = ["-starts_at", "-id"]

    def __str__(self):
        return self.title

    @property
    def phase(self):
        """upcoming / live / ended, derived from the window for scheduled exams."""
        if self.status != self.Status.SCHEDULED:
            return self.status
        now = timezone.now()
        if now < self.starts_at:
            return "upcoming"
        if now >= self.ends_at:
            return "ended"
        return "live"


class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="exam_questions")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="+")
    order = models.PositiveIntegerField(default=0)
    marks_override = models.DecimalField(**MARKS, null=True, blank=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["exam", "question"], name="uniq_exam_question")
        ]

    @property
    def marks(self):
        return self.marks_override if self.marks_override is not None else self.question.marks


class Attempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        GRADING = "grading", "Awaiting grading"
        GRADED = "graded", "Graded"

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exam_attempts"
    )
    attempt_number = models.PositiveSmallIntegerField(default=1)
    started_at = models.DateTimeField(default=timezone.now)
    deadline_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    auto_submitted = models.BooleanField(default=False)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True
    )
    question_order = models.JSONField(default=list)
    option_orders = models.JSONField(default=dict)
    objective_score = models.DecimalField(**MARKS, default=Decimal("0"))
    subjective_score = models.DecimalField(**MARKS, default=Decimal("0"))
    total_score = models.DecimalField(**MARKS, default=Decimal("0"))
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    passed = models.BooleanField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "student", "attempt_number"], name="uniq_attempt_number"
            )
        ]
        indexes = [models.Index(fields=["exam", "student"])]

    def __str__(self):
        return f"{self.student_id} on {self.exam_id} #{self.attempt_number}"


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    exam_question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE, related_name="+")
    selected_options = models.ManyToManyField(Option, blank=True, related_name="+")
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    marks_awarded = models.DecimalField(**MARKS, null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    grader_feedback = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "exam_question"], name="uniq_answer")
        ]


class IntegrityEvent(models.Model):
    class Kind(models.TextChoices):
        TAB_SWITCH = "tab_switch", "Switched tab"
        FULLSCREEN_EXIT = "fullscreen_exit", "Left full screen"
        WINDOW_BLUR = "window_blur", "Window lost focus"
        COPY = "copy", "Copy"
        PASTE = "paste", "Paste"
        DEVTOOLS = "devtools", "Developer tools"

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="integrity_events")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    occurred_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["occurred_at", "id"]
