from django.conf import settings
from rest_framework import serializers

from apps.core.files import SignedFileField

from .enrollment_serializers import StudentBriefSerializer
from .models import Assignment, AssignmentSubmission
from .validators import ASSIGNMENT_EXTENSIONS, validate_upload


def _validate_assignment_file(file):
    if file:
        validate_upload(file, ASSIGNMENT_EXTENSIONS, settings.ASSIGNMENT_UPLOAD_MAX_MB)
    return file


class AssignmentSerializer(serializers.ModelSerializer):
    submission_count = serializers.IntegerField(read_only=True, default=None)
    graded_count = serializers.IntegerField(read_only=True, default=None)
    my_submission = serializers.SerializerMethodField()
    attachment = SignedFileField(required=False, allow_null=True, max_length=255)

    class Meta:
        model = Assignment
        fields = [
            "id",
            "course",
            "title",
            "description",
            "attachment",
            "due_at",
            "max_marks",
            "allow_late",
            "created_by",
            "submission_count",
            "graded_count",
            "my_submission",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["course", "created_by", "created_at", "updated_at"]

    def validate_attachment(self, value):
        return _validate_assignment_file(value)

    def get_my_submission(self, obj) -> dict | None:
        sub = self.context.get("my_submissions", {}).get(obj.pk)
        if not sub:
            return None
        return {
            "id": sub.pk,
            "submitted_at": sub.submitted_at,
            "is_late": sub.is_late,
            "graded": sub.graded_at is not None,
            "marks": str(sub.marks) if sub.marks is not None else None,
        }


class SubmissionSerializer(serializers.ModelSerializer):
    student_detail = StudentBriefSerializer(source="student", read_only=True)
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    max_marks = serializers.DecimalField(
        source="assignment.max_marks", max_digits=6, decimal_places=2, read_only=True
    )
    file = SignedFileField(read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "student",
            "student_detail",
            "file",
            "text",
            "submitted_at",
            "is_late",
            "marks",
            "max_marks",
            "feedback",
            "graded_by",
            "graded_at",
        ]
        read_only_fields = fields


class SubmitSerializer(serializers.Serializer):
    file = serializers.FileField(required=False, allow_null=True)
    text = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_file(self, value):
        return _validate_assignment_file(value)


class GradeSerializer(serializers.Serializer):
    marks = serializers.DecimalField(max_digits=6, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True, default="")
