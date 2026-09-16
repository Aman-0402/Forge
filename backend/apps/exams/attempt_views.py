from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from . import attempts as services
from .attempt_serializers import (
    AnswerInputSerializer,
    IntegrityEventSerializer,
    student_attempt_payload,
)
from .models import Attempt, IntegrityEvent


def own_attempt(request, pk):
    return get_object_or_404(Attempt.objects.select_related("exam"), pk=pk, student=request.user)


class AttemptDetailView(APIView):
    @extend_schema(responses={200: dict})
    def get(self, request, pk):
        attempt = own_attempt(request, pk)
        services.expire_if_overdue(attempt)
        return Response(student_attempt_payload(attempt))


class AnswerView(APIView):
    @extend_schema(request=AnswerInputSerializer, responses={200: dict})
    def put(self, request, pk, eq_pk):
        attempt = own_attempt(request, pk)
        data = AnswerInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        answer = services.save_answer(
            attempt=attempt,
            exam_question_id=eq_pk,
            selected_option_ids=data.validated_data["selected_option_ids"],
            text_answer=data.validated_data["text_answer"],
        )
        attempt.refresh_from_db()
        return Response(
            {
                "exam_question_id": eq_pk,
                "selected_option_ids": list(answer.selected_options.values_list("pk", flat=True)),
                "text_answer": answer.text_answer,
                "seconds_remaining": services.seconds_remaining(attempt),
            }
        )


class SubmitAttemptView(APIView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, pk):
        attempt = own_attempt(request, pk)
        if services.expire_if_overdue(attempt):
            return Response(student_attempt_payload(attempt))
        attempt = services.submit_attempt(attempt=attempt, request=request)
        return Response(student_attempt_payload(attempt))


class IntegrityEventView(APIView):
    @extend_schema(
        request=IntegrityEventSerializer, responses={201: IntegrityEventSerializer, 204: None}
    )
    def post(self, request, pk):
        attempt = own_attempt(request, pk)
        services.expire_if_overdue(attempt)
        if attempt.status != Attempt.Status.IN_PROGRESS:
            raise ValidationError({"detail": ["This attempt is already submitted."]})
        serializer = IntegrityEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not attempt.exam.integrity_tracking:
            return Response(status=status.HTTP_204_NO_CONTENT)
        event = IntegrityEvent.objects.create(attempt=attempt, **serializer.validated_data)
        return Response(IntegrityEventSerializer(event).data, status=status.HTTP_201_CREATED)
