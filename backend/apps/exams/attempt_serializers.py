from rest_framework import serializers

from . import attempts as services
from .models import Attempt, IntegrityEvent


def student_attempt_payload(attempt):
    """What a student sees while taking an exam. Never includes correct answers."""
    exam = attempt.exam
    data = {
        "id": attempt.pk,
        "exam": {
            "id": exam.pk,
            "title": exam.title,
            "duration_minutes": exam.duration_minutes,
            "ends_at": exam.ends_at,
            "integrity_tracking": exam.integrity_tracking,
        },
        "attempt_number": attempt.attempt_number,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "deadline_at": attempt.deadline_at,
        "submitted_at": attempt.submitted_at,
        "auto_submitted": attempt.auto_submitted,
        "seconds_remaining": services.seconds_remaining(attempt),
        "questions": [],
    }
    if attempt.status != Attempt.Status.IN_PROGRESS:
        return data

    rows = {
        eq.pk: eq
        for eq in exam.exam_questions.select_related("question").prefetch_related(
            "question__options"
        )
    }
    answers = {a.exam_question_id: a for a in attempt.answers.prefetch_related("selected_options")}
    for index, eq_pk in enumerate(attempt.question_order, start=1):
        eq = rows.get(eq_pk)
        if eq is None:
            continue
        question = eq.question
        options = {o.pk: o for o in question.options.all()}
        ordered = [options[i] for i in attempt.option_orders.get(str(eq_pk), []) if i in options]
        answer = answers.get(eq_pk)
        data["questions"].append(
            {
                "exam_question_id": eq_pk,
                "index": index,
                "type": question.type,
                "text": question.text,
                "marks": str(eq.marks),
                "negative_marks": str(question.negative_marks),
                "options": [{"id": o.pk, "text": o.text} for o in ordered],
                "answer": {
                    "selected_option_ids": [o.pk for o in answer.selected_options.all()]
                    if answer
                    else [],
                    "text_answer": answer.text_answer if answer else "",
                },
            }
        )
    return data


class AnswerInputSerializer(serializers.Serializer):
    selected_option_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    text_answer = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=20000
    )


class IntegrityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrityEvent
        fields = ["id", "kind", "occurred_at", "metadata"]
        read_only_fields = ["id", "occurred_at"]

    def validate_metadata(self, value):
        if not isinstance(value, dict) or len(str(value)) > 2000:
            raise serializers.ValidationError("Metadata must be a small object.")
        return value
