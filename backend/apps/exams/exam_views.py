from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.audit.mixins import AuditedModelMixin
from apps.audit.services import log_action

from . import exam_services as services
from .eligibility import student_exams
from .exam_serializers import (
    AddQuestionsSerializer,
    ExamQuestionSerializer,
    ExamSerializer,
    ExtendSerializer,
)
from .models import Attempt, Exam, ExamQuestion
from .permissions import is_staff_role, managed_exams


class ExamPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.method in SAFE_METHODS or is_staff_role(request.user)


def exams_for(user):
    base = managed_exams(user) if is_staff_role(user) else student_exams(user)
    return base.select_related("course").prefetch_related(
        Prefetch("exam_questions", queryset=ExamQuestion.objects.select_related("question"))
    )


class ExamViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    serializer_class = ExamSerializer
    permission_classes = [ExamPermission]
    audit_prefix = "exam"
    filterset_fields = ["status", "course"]
    search_fields = ["title", "description"]
    ordering_fields = ["starts_at", "ends_at", "title"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Exam.objects.none()
        qs = exams_for(self.request.user)
        if is_staff_role(self.request.user):
            qs = qs.annotate(attempt_count=Count("attempts", distinct=True))
        return qs.order_by("-starts_at", "-id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated and user.role == "student":
            mine = {}
            for attempt in Attempt.objects.filter(student=user).only("id", "exam_id", "status"):
                mine.setdefault(attempt.exam_id, []).append(attempt)
            context["my_attempts"] = mine
        return context

    def _exam(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def _managed(self):
        if not is_staff_role(self.request.user):
            raise PermissionDenied("Only faculty and administrators can manage exams.")
        return self._exam()

    def _respond(self, exam):
        return Response(self.get_serializer(self._exam()).data)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        self._audit("create", serializer.instance)

    def perform_update(self, serializer):
        services.check_update_allowed(serializer.instance, serializer.validated_data.keys())
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        services.ensure_deletable(instance)
        super().perform_destroy(instance)

    @extend_schema(request=None, responses=ExamSerializer)
    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        exam = services.schedule(actor=request.user, exam=self._managed(), request=request)
        return self._respond(exam)

    @extend_schema(request=None, responses=ExamSerializer)
    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        from .attempts import close_exam

        exam = close_exam(actor=request.user, exam=self._managed(), request=request)
        return self._respond(exam)

    @extend_schema(request=None, responses={200: dict, 201: dict})
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def start(self, request, pk=None):
        from .attempt_serializers import student_attempt_payload
        from .attempts import start_attempt

        if request.user.role != "student":
            raise PermissionDenied("Only students can take exams.")
        attempt, created = start_attempt(student=request.user, exam=self._exam(), request=request)
        return Response(
            student_attempt_payload(attempt),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(request=None, responses=ExamSerializer)
    @action(detail=True, methods=["post"])
    def unschedule(self, request, pk=None):
        exam = services.unschedule(actor=request.user, exam=self._managed(), request=request)
        return self._respond(exam)

    @extend_schema(request=ExtendSerializer, responses=ExamSerializer)
    @action(detail=True, methods=["post"])
    def extend(self, request, pk=None):
        data = ExtendSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        exam = services.extend(
            actor=request.user,
            exam=self._managed(),
            ends_at=data.validated_data["ends_at"],
            request=request,
        )
        return self._respond(exam)


def _managed_exam(request, pk):
    if not is_staff_role(request.user):
        raise PermissionDenied("Only faculty and administrators can manage exams.")
    return get_object_or_404(managed_exams(request.user), pk=pk)


class ExamQuestionsView(generics.GenericAPIView):
    serializer_class = ExamQuestionSerializer
    queryset = ExamQuestion.objects.none()

    @extend_schema(responses=ExamQuestionSerializer(many=True))
    def get(self, request, pk):
        exam = _managed_exam(request, pk)
        rows = exam.exam_questions.select_related("question").prefetch_related("question__options")
        return Response(ExamQuestionSerializer(rows, many=True).data)

    @extend_schema(
        request=AddQuestionsSerializer, responses={201: ExamQuestionSerializer(many=True)}
    )
    def post(self, request, pk):
        exam = _managed_exam(request, pk)
        data = AddQuestionsSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        created = services.add_questions(
            actor=request.user,
            exam=exam,
            question_ids=v["question_ids"],
            bank=v["bank"],
            count=v["count"],
            difficulty=v["difficulty"],
            qtype=v["type"],
            request=request,
        )
        rows = ExamQuestion.objects.filter(pk__in=[eq.pk for eq in created]).select_related(
            "question"
        )
        return Response(
            ExamQuestionSerializer(rows, many=True).data, status=status.HTTP_201_CREATED
        )


class ExamQuestionDetailView(generics.GenericAPIView):
    serializer_class = ExamQuestionSerializer
    queryset = ExamQuestion.objects.none()

    def _row(self, request, pk, eq_pk):
        exam = _managed_exam(request, pk)
        services.ensure_no_attempts(
            exam, "Students have attempted this exam; questions are locked."
        )
        return get_object_or_404(
            ExamQuestion.objects.select_related("question"), exam=exam, pk=eq_pk
        )

    @extend_schema(request=ExamQuestionSerializer, responses=ExamQuestionSerializer)
    def patch(self, request, pk, eq_pk):
        row = self._row(request, pk, eq_pk)
        serializer = ExamQuestionSerializer(row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            request.user,
            "exam.questions.update",
            target=row.exam,
            metadata=request.data,
            request=request,
        )
        return Response(serializer.data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk, eq_pk):
        row = self._row(request, pk, eq_pk)
        log_action(
            request.user,
            "exam.questions.remove",
            target=row.exam,
            metadata={"question": row.question_id},
            request=request,
        )
        row.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
