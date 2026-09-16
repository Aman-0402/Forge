import uuid
from pathlib import Path

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


def _random_name(folder, filename):
    """Store uploads under a random name so URLs cannot be guessed from filenames."""
    return f"{folder}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def course_thumbnail_path(instance, filename):
    return _random_name("courses/thumbnails", filename)


def content_file_path(instance, filename):
    return _random_name("courses/content", filename)


def assignment_attachment_path(instance, filename):
    return _random_name("courses/assignments", filename)


def submission_file_path(instance, filename):
    return _random_name("courses/submissions", filename)


def unique_slug(model, value, instance_pk=None, max_length=220):
    base = slugify(value)[: max_length - 10] or "item"
    slug, n = base, 2
    qs = model.objects.all()
    if instance_pk:
        qs = qs.exclude(pk=instance_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(TimeStampedModel):
    class Kind(models.TextChoices):
        DEPARTMENT = "department", "Department"
        SUBJECT = "subject", "Subject"
        LEVEL = "level", "Level"

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SUBJECT)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Category, self.name, self.pk, 140)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Course(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending_approval", "Pending approval"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class EnrollmentMode(models.TextChoices):
        MANUAL = "manual", "Manual (instructor/admin adds students)"
        OPEN = "open", "Open (students self-enroll)"
        AUTO_DEPARTMENT = "auto_department", "Automatic by department"
        AUTO_BATCH = "auto_batch", "Automatic by batch"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    code = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to=course_thumbnail_path, blank=True, null=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="courses_taught"
    )
    co_instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="courses_co_taught"
    )
    categories = models.ManyToManyField(Category, blank=True, related_name="courses")
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    enrollment_mode = models.CharField(
        max_length=20, choices=EnrollmentMode.choices, default=EnrollmentMode.MANUAL
    )
    auto_enroll_batch = models.CharField(max_length=50, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(Course, self.title, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Module(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Chapter(TimeStampedModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Lesson(TimeStampedModel):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_preview = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class ContentItem(TimeStampedModel):
    class Kind(models.TextChoices):
        VIDEO = "video", "Video"
        PDF = "pdf", "PDF"
        PPT = "ppt", "Presentation"
        DOC = "doc", "Document"
        LINK = "link", "Link"
        TEXT = "text", "Text"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="contents")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to=content_file_path, blank=True, null=True, max_length=255)
    url = models.URLField(blank=True, max_length=500)
    text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Enrollment(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        DROPPED = "dropped", "Dropped"

    class Source(models.TextChoices):
        SELF = "self", "Self"
        MANUAL = "manual", "Manual"
        AUTO = "auto", "Automatic"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    enrolled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-enrolled_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["course", "student"], name="uniq_enrollment")
        ]

    def __str__(self):
        return f"{self.student_id} in {self.course_id}"


class LessonProgress(TimeStampedModel):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="lesson_progress"
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    completed_at = models.DateTimeField(null=True, blank=True)
    last_position_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["enrollment", "lesson"], name="uniq_lesson_progress")
        ]


class Assignment(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to=assignment_attachment_path, blank=True, null=True, max_length=255
    )
    due_at = models.DateTimeField(null=True, blank=True)
    max_marks = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(0)]
    )
    allow_late = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["due_at", "id"]

    def __str__(self):
        return self.title


class AssignmentSubmission(TimeStampedModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment_submissions"
    )
    file = models.FileField(upload_to=submission_file_path, blank=True, null=True, max_length=255)
    text = models.TextField(blank=True)
    submitted_at = models.DateTimeField()
    is_late = models.BooleanField(default=False)
    marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["assignment", "student"], name="uniq_submission")
        ]
