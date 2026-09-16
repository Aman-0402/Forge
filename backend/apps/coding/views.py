from django.db import transaction
from django.db.models import Max, Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from apps.audit.mixins import AuditedModelMixin
from apps.audit.services import log_action

from .models import Language, Problem, TestCase
from .permissions import can_manage_problem, is_staff_role, visible_problems
from .serializers import (
    LanguageSerializer,
    ProblemSerializer,
    TestCaseImportSerializer,
    TestCaseSerializer,
)


class LanguageListView(generics.ListAPIView):
    serializer_class = LanguageSerializer
    queryset = Language.objects.filter(is_enabled=True)
    pagination_class = None


class StaffWritePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.method in SAFE_METHODS or is_staff_role(request.user)

    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or can_manage_problem(request.user, obj)


class ProblemViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    serializer_class = ProblemSerializer
    permission_classes = [StaffWritePermission]
    audit_prefix = "problem"
    filterset_fields = ["difficulty", "status", "course"]
    search_fields = ["title", "statement"]
    ordering_fields = ["title", "created_at", "difficulty"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Problem.objects.none()
        qs = (
            visible_problems(self.request.user)
            .select_related("course")
            .prefetch_related(
                "allowed_languages", Prefetch("test_cases", queryset=TestCase.objects.all())
            )
            .order_by("-created_at", "-id")
        )
        tag = self.request.query_params.get("tag")
        if tag:
            qs = qs.filter(tags__contains=[tag])
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated and user.role == "student":
            from .judging import student_problem_stats

            context["my_stats"] = student_problem_stats(user)
        return context

    @extend_schema(parameters=[OpenApiParameter("tag", str)])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        self._audit("create", serializer.instance)

    def _managed(self):
        problem = get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])
        if not can_manage_problem(self.request.user, problem):
            raise PermissionDenied(
                "Only the problem author, course instructors or an admin can do this."
            )
        return problem

    def _set_status(self, problem, new_status, audit_action):
        problem.status = new_status
        problem.save(update_fields=["status", "updated_at"])
        log_action(self.request.user, audit_action, target=problem, request=self.request)
        return Response(self.get_serializer(self.get_queryset().get(pk=problem.pk)).data)

    @extend_schema(request=None, responses=ProblemSerializer)
    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        problem = self._managed()
        if not problem.test_cases.exists():
            raise ValidationError({"detail": ["Add at least one test case before publishing."]})
        return self._set_status(problem, Problem.Status.PUBLISHED, "problem.publish")

    @extend_schema(request=None, responses=ProblemSerializer)
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._set_status(self._managed(), Problem.Status.ARCHIVED, "problem.archive")

    @extend_schema(request=None, responses=ProblemSerializer)
    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        return self._set_status(self._managed(), Problem.Status.DRAFT, "problem.unpublish")


def _managed_problem(request, pk):
    problem = get_object_or_404(visible_problems(request.user).select_related("course"), pk=pk)
    if not can_manage_problem(request.user, problem):
        raise PermissionDenied(
            "Only the problem author, course instructors or an admin can manage test cases."
        )
    return problem


def _audit_case(request, verb, case, problem):
    log_action(
        request.user,
        f"problem.testcase.{verb}",
        target=problem,
        metadata={
            "test_case": case.pk if case else None,
            "had_submissions": problem.submissions.exists(),
        },
        request=request,
    )


class TestCaseListView(generics.GenericAPIView):
    __test__ = False
    serializer_class = TestCaseSerializer
    queryset = TestCase.objects.none()

    @extend_schema(responses=TestCaseSerializer(many=True))
    def get(self, request, pk):
        problem = _managed_problem(request, pk)
        return Response(TestCaseSerializer(problem.test_cases.all(), many=True).data)

    @extend_schema(request=TestCaseSerializer, responses={201: TestCaseSerializer})
    def post(self, request, pk):
        problem = _managed_problem(request, pk)
        serializer = TestCaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.validated_data.get("order")
        if order is None:
            current = problem.test_cases.aggregate(m=Max("order"))["m"]
            order = 0 if current is None else current + 1
        case = serializer.save(problem=problem, order=order)
        _audit_case(request, "create", case, problem)
        return Response(TestCaseSerializer(case).data, status=status.HTTP_201_CREATED)


class TestCaseImportView(generics.GenericAPIView):
    __test__ = False
    serializer_class = TestCaseImportSerializer
    queryset = TestCase.objects.none()

    @extend_schema(
        request=TestCaseImportSerializer,
        responses={
            201: inline_serializer("TestCaseImportResult", {"created": serializers.IntegerField()})
        },
    )
    def post(self, request, pk):
        problem = _managed_problem(request, pk)
        data = TestCaseImportSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        items, errors = [], {}
        for index, raw in enumerate(data.validated_data["cases"]):
            item = TestCaseSerializer(data=raw)
            if item.is_valid():
                items.append(item)
            else:
                errors[str(index)] = item.errors
        if errors:
            raise ValidationError({"cases": errors})
        start = (problem.test_cases.aggregate(m=Max("order"))["m"] or -1) + 1
        with transaction.atomic():
            for i, item in enumerate(items):
                item.save(problem=problem, order=item.validated_data.get("order", start + i))
        log_action(
            request.user,
            "problem.testcase.import",
            target=problem,
            metadata={"created": len(items)},
            request=request,
        )
        return Response({"created": len(items)}, status=status.HTTP_201_CREATED)


class TestCaseDetailView(generics.GenericAPIView):
    __test__ = False
    serializer_class = TestCaseSerializer
    queryset = TestCase.objects.none()

    def _case(self, request, pk):
        case = get_object_or_404(TestCase.objects.select_related("problem__course"), pk=pk)
        _managed_problem(request, case.problem_id)
        return case

    @extend_schema(request=TestCaseSerializer, responses=TestCaseSerializer)
    def patch(self, request, pk):
        case = self._case(request, pk)
        serializer = TestCaseSerializer(case, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _audit_case(request, "update", case, case.problem)
        return Response(serializer.data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        case = self._case(request, pk)
        problem = case.problem
        _audit_case(request, "delete", case, problem)
        case.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
