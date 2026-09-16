from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .bank_serializers import QuestionSerializer
from .models import Exam, ExamQuestion, Question

User = get_user_model()


class ExamSerializer(serializers.ModelSerializer):
    total_marks = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    phase = serializers.CharField(read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True, default=None)
    allowed_students = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="student"), many=True, required=False
    )
    attempt_count = serializers.SerializerMethodField()
    my_attempts = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "description",
            "course",
            "course_title",
            "created_by",
            "starts_at",
            "ends_at",
            "duration_minutes",
            "pass_marks",
            "shuffle_questions",
            "shuffle_options",
            "max_attempts",
            "show_result_immediately",
            "reveal_answers",
            "integrity_tracking",
            "results_released_at",
            "status",
            "phase",
            "allowed_students",
            "total_marks",
            "question_count",
            "attempt_count",
            "my_attempts",
            "can_manage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_by",
            "results_released_at",
            "status",
            "created_at",
            "updated_at",
        ]

    def _eqs(self, obj):
        return list(obj.exam_questions.all())

    def get_total_marks(self, obj) -> str:
        total = sum((eq.marks for eq in self._eqs(obj)), Decimal("0"))
        return f"{total:.2f}"

    def get_question_count(self, obj) -> int:
        return len(self._eqs(obj))

    def get_attempt_count(self, obj) -> int | None:
        return getattr(obj, "attempt_count", None)

    def get_my_attempts(self, obj) -> dict | None:
        mine = self.context.get("my_attempts")
        if mine is None:
            return None
        attempts = mine.get(obj.pk, [])
        in_progress = next((a for a in attempts if a.status == "in_progress"), None)
        can_start = obj.phase == "live" and (
            in_progress is not None or len(attempts) < obj.max_attempts
        )
        return {
            "used": len(attempts),
            "max": obj.max_attempts,
            "in_progress_id": in_progress.pk if in_progress else None,
            "can_start": can_start,
        }

    def get_can_manage(self, obj) -> bool:
        from .permissions import can_manage_exam

        return can_manage_exam(self.context["request"].user, obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context["request"].user
        if user.role == "student":
            data.pop("attempt_count", None)
            data.pop("allowed_students", None)
        else:
            data.pop("my_attempts", None)
        return data

    def validate_course(self, course):
        from apps.courses.permissions import can_manage_course

        if course and not can_manage_course(self.context["request"].user, course):
            raise serializers.ValidationError("You can only attach exams to courses you teach.")
        return course

    def validate(self, attrs):
        inst = self.instance
        starts = attrs.get("starts_at", getattr(inst, "starts_at", None))
        ends = attrs.get("ends_at", getattr(inst, "ends_at", None))
        if starts and ends and ends <= starts:
            raise serializers.ValidationError({"ends_at": ["Must be after starts_at."]})
        duration = attrs.get("duration_minutes", getattr(inst, "duration_minutes", None))
        if duration is not None and duration < 1:
            raise serializers.ValidationError({"duration_minutes": ["Must be at least 1 minute."]})
        return attrs


class ExamQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    marks = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = ExamQuestion
        fields = ["id", "order", "marks_override", "marks", "question"]


class AddQuestionsSerializer(serializers.Serializer):
    question_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    bank = serializers.IntegerField(required=False, allow_null=True, default=None)
    count = serializers.IntegerField(required=False, min_value=1, default=1)
    difficulty = serializers.ChoiceField(
        choices=Question.Difficulty.choices, required=False, allow_blank=True, default=""
    )
    type = serializers.ChoiceField(
        choices=Question.Type.choices, required=False, allow_blank=True, default=""
    )


class ExtendSerializer(serializers.Serializer):
    ends_at = serializers.DateTimeField()
