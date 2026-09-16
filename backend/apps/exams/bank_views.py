from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from apps.audit.mixins import AuditedModelMixin
from apps.audit.services import log_action

from .bank_serializers import ImportSerializer, QuestionBankSerializer, QuestionSerializer
from .models import Attempt, ExamQuestion, Question, QuestionBank
from .permissions import IsAdminOrFacultyRole, can_edit_bank, readable_banks

LOCKED_EDIT_FIELDS = {"is_active"}


class QuestionBankViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    serializer_class = QuestionBankSerializer
    permission_classes = [IsAdminOrFacultyRole]
    audit_prefix = "question_bank"
    filterset_fields = ["course", "is_shared", "owner"]
    search_fields = ["title", "description"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return QuestionBank.objects.none()
        return (
            readable_banks(self.request.user)
            .select_related("owner")
            .annotate(question_count=Count("questions"))
            .order_by("title", "id")
        )

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in SAFE_METHODS and not can_edit_bank(request.user, obj):
            raise PermissionDenied("Only the bank owner or an admin can change it.")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        self._audit("create", serializer.instance)

    def perform_destroy(self, instance):
        if ExamQuestion.objects.filter(question__bank=instance).exists():
            raise ValidationError({"detail": ["Questions from this bank are used in exams."]})
        super().perform_destroy(instance)

    @extend_schema(
        request=ImportSerializer,
        responses={201: inline_serializer("ImportResult", {"created": serializers.IntegerField()})},
    )
    @action(detail=True, methods=["post"], url_path="import")
    def import_questions(self, request, pk=None):
        bank = self.get_object()
        data = ImportSerializer(data=request.data)
        data.is_valid(raise_exception=True)

        serializers_ok, errors = [], {}
        for index, raw in enumerate(data.validated_data["questions"]):
            item = QuestionSerializer(data=raw)
            if item.is_valid():
                serializers_ok.append(item)
            else:
                errors[str(index)] = item.errors
        if errors:
            raise ValidationError({"questions": errors})

        with transaction.atomic():
            for item in serializers_ok:
                item.save(bank=bank)
        log_action(
            request.user,
            "question_bank.import",
            target=bank,
            metadata={"created": len(serializers_ok)},
            request=request,
        )
        return Response({"created": len(serializers_ok)}, status=status.HTTP_201_CREATED)


class BankQuestionsView(generics.ListCreateAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsAdminOrFacultyRole]
    filterset_fields = ["type", "difficulty", "is_active"]
    search_fields = ["text", "explanation"]

    def get_bank(self):
        bank = get_object_or_404(readable_banks(self.request.user), pk=self.kwargs["pk"])
        if self.request.method not in SAFE_METHODS and not can_edit_bank(self.request.user, bank):
            raise PermissionDenied("Only the bank owner or an admin can add questions.")
        return bank

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Question.objects.none()
        qs = (
            Question.objects.filter(bank=self.get_bank())
            .prefetch_related("options")
            .annotate(used_in_exams=Count("exams", distinct=True))
            .order_by("id")
        )
        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__contains=[tag])
        return qs

    def perform_create(self, serializer):
        serializer.save(bank=self.get_bank())
        log_action(
            self.request.user, "question.create", target=serializer.instance, request=self.request
        )


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsAdminOrFacultyRole]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Question.objects.none()
        return Question.objects.filter(bank__in=readable_banks(self.request.user)).prefetch_related(
            "options"
        )

    def get_object(self):
        question = super().get_object()
        if self.request.method not in SAFE_METHODS and not can_edit_bank(
            self.request.user, question.bank
        ):
            raise PermissionDenied("Only the bank owner or an admin can change this question.")
        return question

    def perform_update(self, serializer):
        question = serializer.instance
        attempted = Attempt.objects.filter(exam__exam_questions__question=question).exists()
        if attempted and not set(serializer.validated_data) <= LOCKED_EDIT_FIELDS:
            raise ValidationError(
                {
                    "detail": [
                        "Students have attempted an exam with this question. "
                        "Create a new question instead; you can still deactivate this one."
                    ]
                }
            )
        serializer.save()
        log_action(
            self.request.user,
            "question.update",
            target=question,
            metadata={"fields": sorted(serializer.validated_data)},
            request=self.request,
        )

    def perform_destroy(self, instance):
        if ExamQuestion.objects.filter(question=instance).exists():
            raise ValidationError(
                {"detail": ["This question is used in an exam. Deactivate it instead."]}
            )
        log_action(self.request.user, "question.delete", target=instance, request=self.request)
        instance.delete()
