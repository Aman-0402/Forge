from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Course

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name"]

    def get_name(self, obj) -> str:
        return obj.get_full_name() or obj.email


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "kind", "parent"]
        read_only_fields = ["slug"]


class CategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class CourseSerializer(serializers.ModelSerializer):
    instructor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="faculty", is_active=True), required=False
    )
    instructor_detail = UserBriefSerializer(source="instructor", read_only=True)
    co_instructors = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, required=False
    )
    co_instructors_detail = UserBriefSerializer(source="co_instructors", many=True, read_only=True)
    categories_detail = CategoryBriefSerializer(source="categories", many=True, read_only=True)
    department_code = serializers.CharField(source="department.code", read_only=True, default=None)
    lesson_count = serializers.IntegerField(read_only=True, default=0)
    enrollment_count = serializers.IntegerField(read_only=True, default=0)
    is_enrolled = serializers.SerializerMethodField()
    my_progress = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "slug",
            "code",
            "description",
            "thumbnail",
            "instructor",
            "instructor_detail",
            "co_instructors",
            "co_instructors_detail",
            "categories",
            "categories_detail",
            "department",
            "department_code",
            "level",
            "status",
            "rejection_reason",
            "submitted_at",
            "approved_at",
            "enrollment_mode",
            "auto_enroll_batch",
            "start_date",
            "end_date",
            "lesson_count",
            "enrollment_count",
            "is_enrolled",
            "my_progress",
            "can_manage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "slug",
            "status",
            "rejection_reason",
            "submitted_at",
            "approved_at",
            "created_at",
            "updated_at",
        ]

    # --- per-user fields (enrollments map is built once per request by the view) ---

    def _my_enrollment(self, obj):
        return self.context.get("my_enrollments", {}).get(obj.pk)

    def get_is_enrolled(self, obj) -> bool:
        return self._my_enrollment(obj) is not None

    def get_my_progress(self, obj) -> int | None:
        enrollment = self._my_enrollment(obj)
        return enrollment.progress_percent if enrollment else None

    def get_can_manage(self, obj) -> bool:
        from .permissions import can_manage_course

        return can_manage_course(self.context["request"].user, obj)

    # --- validation ---

    def validate_co_instructors(self, value):
        bad = [u.email for u in value if u.role != "faculty"]
        if bad:
            raise serializers.ValidationError(f"Co-instructors must be faculty: {', '.join(bad)}.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if user.role == "faculty":
            if self.instance is None:
                attrs["instructor"] = user
            else:
                attrs.pop("instructor", None)
        elif self.instance is None and not attrs.get("instructor"):
            raise serializers.ValidationError({"instructor": ["Choose a faculty instructor."]})

        instructor = attrs.get("instructor") or getattr(self.instance, "instructor", None)
        if "co_instructors" in attrs and instructor:
            attrs["co_instructors"] = [u for u in attrs["co_instructors"] if u.pk != instructor.pk]

        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": ["Must be on or after start_date."]})

        mode = attrs.get("enrollment_mode", getattr(self.instance, "enrollment_mode", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        batch = attrs.get("auto_enroll_batch", getattr(self.instance, "auto_enroll_batch", ""))
        if mode == Course.EnrollmentMode.AUTO_DEPARTMENT and not department:
            raise serializers.ValidationError({"department": ["Required for auto_department."]})
        if mode == Course.EnrollmentMode.AUTO_BATCH and not batch:
            raise serializers.ValidationError({"auto_enroll_batch": ["Required for auto_batch."]})
        return attrs


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, required=False, default="")
