from rest_framework import serializers

from .models import Language, Problem, TestCase


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = [
            "id",
            "name",
            "slug",
            "version",
            "judge0_id",
            "editor_mode",
            "default_template",
            "is_enabled",
        ]
        read_only_fields = ["id"]


class ProblemSerializer(serializers.ModelSerializer):
    allowed_languages = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(), many=True, required=False
    )
    languages = serializers.SerializerMethodField()
    sample_cases = serializers.SerializerMethodField()
    test_case_count = serializers.SerializerMethodField()
    course_title = serializers.CharField(source="course.title", read_only=True, default=None)
    can_manage = serializers.SerializerMethodField()
    my_status = serializers.SerializerMethodField()

    class Meta:
        model = Problem
        fields = [
            "id",
            "title",
            "slug",
            "statement",
            "input_format",
            "output_format",
            "constraints",
            "difficulty",
            "tags",
            "time_limit_seconds",
            "memory_limit_kb",
            "max_score",
            "allow_partial",
            "course",
            "course_title",
            "created_by",
            "status",
            "allowed_languages",
            "languages",
            "visible_from",
            "visible_until",
            "sample_cases",
            "test_case_count",
            "can_manage",
            "my_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "created_by", "status", "created_at", "updated_at"]

    def get_languages(self, obj) -> list:
        return LanguageSerializer(obj.languages(), many=True).data

    def get_sample_cases(self, obj) -> list:
        return [
            {"input": c.input, "expected_output": c.expected_output, "explanation": c.explanation}
            for c in obj.test_cases.all()
            if c.is_sample and not c.is_hidden
        ]

    def get_test_case_count(self, obj) -> int:
        return len(obj.test_cases.all())

    def get_can_manage(self, obj) -> bool:
        from .permissions import can_manage_problem

        return can_manage_problem(self.context["request"].user, obj)

    def get_my_status(self, obj) -> dict | None:
        stats = self.context.get("my_stats")
        if stats is None:
            return None
        return stats.get(obj.pk, {"attempts": 0, "best_score": 0, "solved": False})

    def validate_tags(self, value):
        if not isinstance(value, list) or not all(isinstance(t, str) for t in value):
            raise serializers.ValidationError("Tags must be a list of strings.")
        return [t.strip() for t in value if t.strip()]

    def validate_allowed_languages(self, value):
        disabled = [lang.name for lang in value if not lang.is_enabled]
        if disabled:
            raise serializers.ValidationError(f"Disabled languages: {', '.join(disabled)}.")
        return value

    def validate_course(self, course):
        from apps.courses.permissions import can_manage_course

        if course and not can_manage_course(self.context["request"].user, course):
            raise serializers.ValidationError("You can only attach problems to courses you teach.")
        return course

    def validate(self, attrs):
        inst = self.instance
        start = attrs.get("visible_from", getattr(inst, "visible_from", None))
        end = attrs.get("visible_until", getattr(inst, "visible_until", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"visible_until": ["Must be after visible_from."]})
        return attrs


class TestCaseSerializer(serializers.ModelSerializer):
    __test__ = False

    class Meta:
        model = TestCase
        fields = [
            "id",
            "problem",
            "input",
            "expected_output",
            "is_sample",
            "is_hidden",
            "weight",
            "order",
            "explanation",
        ]
        read_only_fields = ["id", "problem"]
        extra_kwargs = {"order": {"required": False}, "is_hidden": {"required": False}}

    def validate(self, attrs):
        inst = self.instance
        is_sample = attrs.get("is_sample", getattr(inst, "is_sample", False))
        hidden_given = "is_hidden" in getattr(self, "initial_data", {})
        if is_sample and not hidden_given and "is_sample" in attrs:
            attrs["is_hidden"] = False
        is_hidden = attrs.get("is_hidden", getattr(inst, "is_hidden", True))
        if is_sample and is_hidden:
            raise serializers.ValidationError(
                {"is_hidden": ["Sample cases are shown to students, so they cannot be hidden."]}
            )
        return attrs


class TestCaseImportSerializer(serializers.Serializer):
    cases = serializers.ListField(child=serializers.DictField(), allow_empty=False, max_length=200)
