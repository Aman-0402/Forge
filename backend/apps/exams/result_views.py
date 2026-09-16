from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsStudent

from . import results as services
from .models import Answer, Attempt
from .permissions import can_manage_exam, is_staff_role, managed_exams


def _managed_exam(request, pk):
    if not is_staff_role(request.user):
        raise PermissionDenied("Only faculty and administrators can do this.")
    return get_object_or_404(managed_exams(request.user), pk=pk)


class AttemptRowSerializer(serializers.ModelSerializer):
    student_detail = serializers.SerializerMethodField()
    integrity_event_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id",
            "student",
            "student_detail",
            "attempt_number",
            "status",
            "started_at",
            "deadline_at",
            "submitted_at",
            "auto_submitted",
            "objective_score",
            "subjective_score",
            "total_score",
            "percentage",
            "passed",
            "integrity_event_count",
        ]

    def get_student_detail(self, obj) -> dict:
        profile = getattr(obj.student, "student_profile", None)
        return {
            "id": obj.student_id,
            "email": obj.student.email,
            "name": obj.student.get_full_name() or obj.student.email,
            "roll_number": profile.roll_number if profile else None,
        }


class ExamAttemptsView(generics.ListAPIView):
    serializer_class = AttemptRowSerializer
    filterset_fields = ["status"]

    @extend_schema(parameters=[OpenApiParameter("status", str)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Attempt.objects.none()
        exam = _managed_exam(self.request, self.kwargs["pk"])
        return (
            Attempt.objects.filter(exam=exam)
            .select_related("student__student_profile")
            .annotate(integrity_event_count=Count("integrity_events"))
            .order_by("status", "-submitted_at", "-id")
        )


def _managed_attempt(request, pk):
    attempt = get_object_or_404(Attempt.objects.select_related("exam", "student"), pk=pk)
    if not is_staff_role(request.user) or not can_manage_exam(request.user, attempt.exam):
        raise Http404
    return attempt


class AttemptReviewView(APIView):
    @extend_schema(responses={200: dict})
    def get(self, request, pk):
        return Response(services.review_payload(_managed_attempt(request, pk)))


class GradeInputSerializer(serializers.Serializer):
    marks_awarded = serializers.DecimalField(max_digits=6, decimal_places=2)
    grader_feedback = serializers.CharField(required=False, allow_blank=True, default="")


class GradeAnswerView(APIView):
    @extend_schema(request=GradeInputSerializer, responses={200: dict})
    def patch(self, request, pk):
        answer = get_object_or_404(Answer.objects.select_related("attempt__exam"), pk=pk)
        if not is_staff_role(request.user) or not can_manage_exam(
            request.user, answer.attempt.exam
        ):
            raise Http404
        data = GradeInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        answer = services.grade_answer(
            actor=request.user, answer=answer, request=request, **data.validated_data
        )
        attempt = answer.attempt
        attempt.refresh_from_db()
        return Response(
            {
                "answer_id": answer.pk,
                "marks_awarded": services.fmt(answer.marks_awarded),
                "grader_feedback": answer.grader_feedback,
                "attempt": {
                    "id": attempt.pk,
                    "status": attempt.status,
                    "total_score": services.fmt(attempt.total_score),
                    "percentage": services.fmt(attempt.percentage),
                    "passed": attempt.passed,
                },
            }
        )


class AttemptResultView(APIView):
    @extend_schema(responses={200: dict})
    def get(self, request, pk):
        attempt = get_object_or_404(Attempt.objects.select_related("exam", "student"), pk=pk)
        if attempt.student_id == request.user.pk:
            if not services.result_visible(attempt):
                raise PermissionDenied("Results for this exam are not released yet.")
            return Response(services.result_payload(attempt, reveal=attempt.exam.reveal_answers))
        if is_staff_role(request.user) and can_manage_exam(request.user, attempt.exam):
            return Response(services.result_payload(attempt, reveal=True))
        raise Http404


class ReleaseResultsView(APIView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, pk):
        from .exam_serializers import ExamSerializer
        from .exam_views import exams_for

        exam = services.release_results(
            actor=request.user, exam=_managed_exam(request, pk), request=request
        )
        exam = exams_for(request.user).get(pk=exam.pk)
        return Response(ExamSerializer(exam, context={"request": request}).data)


class ExamResultsView(APIView):
    @extend_schema(responses={200: dict})
    def get(self, request, pk):
        return Response(services.summary(_managed_exam(request, pk)))


class ExamResultsExportView(APIView):
    @extend_schema(responses={(200, "text/csv"): str})
    def get(self, request, pk):
        exam = _managed_exam(request, pk)
        response = HttpResponse(services.export_csv(exam), content_type="text/csv; charset=utf-8")
        name = slugify(exam.title) or f"exam-{exam.pk}"
        response["Content-Disposition"] = f'attachment; filename="{name}-results.csv"'
        return response


class MyResultRowSerializer(serializers.Serializer):
    attempt_id = serializers.IntegerField()
    exam = serializers.DictField()
    attempt_number = serializers.IntegerField()
    status = serializers.CharField()
    submitted_at = serializers.DateTimeField(allow_null=True)
    result_visible = serializers.BooleanField()
    total_score = serializers.CharField(allow_null=True)
    percentage = serializers.CharField(allow_null=True)
    passed = serializers.BooleanField(allow_null=True)


class MyResultsView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = MyResultRowSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Attempt.objects.none()
        return (
            Attempt.objects.filter(student=self.request.user)
            .exclude(status=Attempt.Status.IN_PROGRESS)
            .select_related("exam")
            .order_by("-submitted_at", "-id")
        )

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        rows = []
        for attempt in page:
            visible = services.result_visible(attempt)
            rows.append(
                {
                    "attempt_id": attempt.pk,
                    "exam": {"id": attempt.exam_id, "title": attempt.exam.title},
                    "attempt_number": attempt.attempt_number,
                    "status": attempt.status,
                    "submitted_at": attempt.submitted_at,
                    "result_visible": visible,
                    "total_score": services.fmt(attempt.total_score) if visible else None,
                    "percentage": services.fmt(attempt.percentage) if visible else None,
                    "passed": attempt.passed if visible else None,
                }
            )
        return self.get_paginated_response(rows)
