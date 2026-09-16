from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    class Kind(models.TextChoices):
        INFO = "info", "Info"
        ACCOUNT = "account", "Account"
        ENROLLMENT = "enrollment", "Enrollment"
        EXAM = "exam", "Exam"
        RESULT = "result", "Result"
        ASSIGNMENT = "assignment", "Assignment"
        CODING = "coding", "Coding"
        ANNOUNCEMENT = "announcement", "Announcement"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.INFO)
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.recipient_id}: {self.title}"


class ContactMessage(models.Model):
    """A message from the public contact form. Not tied to a user account."""

    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Announcement(models.Model):
    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        FACULTY = "faculty", "Faculty"
        STUDENTS = "students", "Students"
        DEPARTMENT = "department", "Department"
        COURSE = "course", "Course"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="announcements",
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(
        max_length=20, choices=Audience.choices, default=Audience.ALL, db_index=True
    )
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
    )
    published_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    # Set once notifications are sent; scheduled posts stay null until they go live.
    delivered_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self):
        return self.title
