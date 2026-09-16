from django.db import transaction
from rest_framework import serializers

from .models import Option, Question, QuestionBank


class QuestionBankSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True, default=0)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = QuestionBank
        fields = [
            "id",
            "title",
            "description",
            "owner",
            "owner_name",
            "course",
            "is_shared",
            "question_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["owner", "created_at", "updated_at"]

    def get_owner_name(self, obj) -> str:
        return obj.owner.get_full_name() or obj.owner.email


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "text", "is_correct", "order"]
        read_only_fields = ["id"]
        extra_kwargs = {"order": {"required": False}}


def validate_question_shape(qtype, options, marks, negative_marks):
    """Return a dict of field errors (empty when valid)."""
    errors = {}
    if negative_marks is not None and marks is not None and negative_marks > marks:
        errors["negative_marks"] = ["Cannot exceed the question's marks."]
    if qtype == Question.Type.SUBJECTIVE:
        if options:
            errors["options"] = ["Written-answer questions have no options."]
        return errors

    correct = sum(1 for o in options if o.get("is_correct"))
    if len(options) < 2:
        errors["options"] = ["Add at least two options."]
    elif correct == 0:
        errors["options"] = ["Mark at least one option as correct."]
    elif qtype in (Question.Type.MCQ_SINGLE, Question.Type.TRUE_FALSE) and correct != 1:
        errors["options"] = ["Exactly one option must be correct."]
    elif qtype == Question.Type.TRUE_FALSE and len(options) != 2:
        errors["options"] = ["True/false questions have exactly two options."]
    return errors


class QuestionSerializer(serializers.ModelSerializer):
    """Staff view of a question, including which options are correct."""

    options = OptionSerializer(many=True, required=False)
    used_in_exams = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = Question
        fields = [
            "id",
            "bank",
            "type",
            "text",
            "marks",
            "negative_marks",
            "difficulty",
            "explanation",
            "tags",
            "is_active",
            "options",
            "used_in_exams",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["bank", "created_at", "updated_at"]

    def validate_tags(self, value):
        if not isinstance(value, list) or not all(isinstance(t, str) for t in value):
            raise serializers.ValidationError("Tags must be a list of strings.")
        return [t.strip() for t in value if t.strip()]

    def validate(self, attrs):
        inst = self.instance
        qtype = attrs.get("type", getattr(inst, "type", None))
        marks = attrs.get("marks", getattr(inst, "marks", None))
        negative = attrs.get("negative_marks", getattr(inst, "negative_marks", 0))
        if "options" in attrs:
            options = attrs["options"]
        elif inst is not None:
            options = [{"is_correct": o.is_correct} for o in inst.options.all()]
        else:
            options = []
        errors = validate_question_shape(qtype, options, marks, negative)
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    @staticmethod
    def _write_options(question, options):
        question.options.all().delete()
        Option.objects.bulk_create(
            [
                Option(
                    question=question,
                    text=o["text"],
                    is_correct=o.get("is_correct", False),
                    order=o.get("order", i),
                )
                for i, o in enumerate(options)
            ]
        )

    @transaction.atomic
    def create(self, validated_data):
        options = validated_data.pop("options", [])
        question = Question.objects.create(**validated_data)
        self._write_options(question, options)
        return question

    @transaction.atomic
    def update(self, instance, validated_data):
        options = validated_data.pop("options", None)
        instance = super().update(instance, validated_data)
        if options is not None:
            self._write_options(instance, options)
        return instance


class ImportSerializer(serializers.Serializer):
    questions = serializers.ListField(
        child=serializers.DictField(), allow_empty=False, max_length=500
    )
