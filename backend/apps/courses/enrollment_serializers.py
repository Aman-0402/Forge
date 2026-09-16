from rest_framework import serializers

from .models import Course, Enrollment
from .serializers import UserBriefSerializer


class CourseBriefSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ["id", "title", "slug", "code", "thumbnail", "level", "status", "instructor_name"]

    def get_instructor_name(self, obj) -> str:
        return obj.instructor.get_full_name() or obj.instructor.email


class StudentBriefSerializer(UserBriefSerializer):
    roll_number = serializers.CharField(
        source="student_profile.roll_number", read_only=True, default=None
    )
    batch = serializers.CharField(source="student_profile.batch", read_only=True, default=None)

    class Meta(UserBriefSerializer.Meta):
        fields = [*UserBriefSerializer.Meta.fields, "roll_number", "batch"]


class EnrollmentSerializer(serializers.ModelSerializer):
    course_detail = CourseBriefSerializer(source="course", read_only=True)
    student_detail = StudentBriefSerializer(source="student", read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "course",
            "course_detail",
            "student",
            "student_detail",
            "status",
            "source",
            "enrolled_at",
            "completed_at",
            "progress_percent",
        ]
        read_only_fields = fields


class BulkEnrollSerializer(serializers.Serializer):
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    batch = serializers.CharField(required=False, allow_blank=True, default="")
    department = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        if not (attrs["student_ids"] or attrs["batch"] or attrs["department"]):
            raise serializers.ValidationError("Give student_ids, batch or department.")
        return attrs


class BulkEnrollResultSerializer(serializers.Serializer):
    enrolled = serializers.ListField(child=serializers.IntegerField())
    already_enrolled = serializers.ListField(child=serializers.IntegerField())
    invalid = serializers.ListField(child=serializers.IntegerField())
