from django.conf import settings
from django.db import models


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
