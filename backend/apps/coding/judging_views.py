from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.permissions import IsStudent

from . import judge0, judging
from .models import CodeSubmission, Language
from .permissions import can_attempt_problem, can_manage_problem, visible_problems

UNAVAILABLE = "The code runner is unavailable right now. Try again in a minute."


class CodeInputSerializer(serializers.Serializer):
    language = serializers.PrimaryKeyRelatedField(queryset=Language.objects.filter(is_enabled=True))
    source_code = serializers.CharField(trim_whitespace=False, allow_blank=True)


class RunInputSerializer(CodeInputSerializer):
    stdin = serializers.CharField(
        required=False, allow_null=True, trim_whitespace=False, allow_blank=True
    )


def _problem(request, pk):
    return get_object_or_404(
        visible_problems(request.user).prefetch_related("test_cases", "allowed_languages"), pk=pk
    )


class RunView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "code_run"

    @extend_schema(request=RunInputSerializer, responses={200: dict})
    def post(self, request, pk):
        problem = _problem(request, pk)
        manager = can_manage_problem(request.user, problem)
        if not manager and not (
            request.user.role == "student" and can_attempt_problem(request.user, problem)
        ):
            raise PermissionDenied("You cannot run code on this problem.")
        data = RunInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            result = judging.run_code(problem=problem, **data.validated_data)
        except judge0.Judge0Error:
            return Response(
                {"detail": UNAVAILABLE, "code": "judge_unavailable", "errors": {}}, status=503
            )
        return Response(result)


def result_rows(submission, *, reveal_hidden):
    rows = []
    for index, result in enumerate(submission.results.select_related("test_case"), start=1):
        case = result.test_case
        row = {
            "index": index,
            "verdict": result.verdict,
            "passed": result.passed,
            "time_seconds": result.time_seconds,
            "memory_kb": result.memory_kb,
            "hidden": bool(case and case.is_hidden),
            "is_sample": bool(case and case.is_sample),
        }
        if reveal_hidden or (case and not case.is_hidden):
            row.update(
                {
                    "input": case.input if case else "",
                    "expected_output": case.expected_output if case else "",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
        rows.append(row)
    return rows


class SubmissionRowSerializer(serializers.ModelSerializer):
    language_name = serializers.CharField(source="language.name", read_only=True)
    student_name = serializers.SerializerMethodField()
    problem_title = serializers.CharField(source="problem.title", read_only=True)

    class Meta:
        model = CodeSubmission
        fields = [
            "id",
            "problem",
            "problem_title",
            "student",
            "student_name",
            "language",
            "language_name",
            "status",
            "verdict",
            "score",
            "passed_count",
            "total_count",
            "max_time_seconds",
            "max_memory_kb",
            "submitted_at",
            "judged_at",
        ]

    def get_student_name(self, obj) -> str:
        return obj.student.get_full_name() or obj.student.email


def submission_payload(submission, *, reveal_hidden):
    data = dict(SubmissionRowSerializer(submission).data)
    data["source_code"] = submission.source_code
    data["compile_output"] = submission.compile_output
    data["results"] = result_rows(submission, reveal_hidden=reveal_hidden)
    return data


class SubmitView(APIView):
    permission_classes = [IsStudent]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "code_submit"

    @extend_schema(request=CodeInputSerializer, responses={201: dict, 503: dict})
    def post(self, request, pk):
        problem = _problem(request, pk)
        if not can_attempt_problem(request.user, problem):
            raise PermissionDenied("This problem is not open for submissions.")
        data = CodeInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            submission = judging.submit_code(
                student=request.user, problem=problem, request=request, **data.validated_data
            )
        except judge0.Judge0Error:
            latest = CodeSubmission.objects.filter(student=request.user, problem=problem).first()
            return Response(
                {
                    "detail": UNAVAILABLE,
                    "code": "judge_unavailable",
                    "errors": {},
                    "submission_id": latest.pk if latest else None,
                },
                status=503,
            )
        return Response(
            submission_payload(submission, reveal_hidden=False), status=status.HTTP_201_CREATED
        )


class ProblemSubmissionsView(generics.ListAPIView):
    serializer_class = SubmissionRowSerializer

    @extend_schema(parameters=[OpenApiParameter("student", int), OpenApiParameter("verdict", str)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CodeSubmission.objects.none()
        problem = _problem(self.request, self.kwargs["pk"])
        qs = problem.submissions.select_related("language", "student", "problem")
        if can_manage_problem(self.request.user, problem):
            student = self.request.query_params.get("student")
            if student:
                qs = qs.filter(student_id=student)
        else:
            qs = qs.filter(student=self.request.user)
        verdict = self.request.query_params.get("verdict")
        if verdict:
            qs = qs.filter(verdict=verdict)
        return qs


class SubmissionDetailView(APIView):
    @extend_schema(responses={200: dict})
    def get(self, request, pk):
        submission = get_object_or_404(
            CodeSubmission.objects.select_related("problem__course", "language", "student"), pk=pk
        )
        if submission.student_id == request.user.pk:
            return Response(submission_payload(submission, reveal_hidden=False))
        if can_manage_problem(request.user, submission.problem):
            return Response(submission_payload(submission, reveal_hidden=True))
        raise Http404


class RejudgeView(APIView):
    @extend_schema(
        request=None,
        responses=inline_serializer(
            "RejudgeResult",
            {"rejudged": serializers.IntegerField(), "failed": serializers.IntegerField()},
        ),
    )
    def post(self, request, pk):
        problem = _problem(request, pk)
        if not can_manage_problem(request.user, problem):
            raise PermissionDenied(
                "Only the problem author, course instructors or an admin can rejudge."
            )
        return Response(
            judging.rejudge_problem(actor=request.user, problem=problem, request=request)
        )


class LeaderboardView(APIView):
    @extend_schema(responses={200: dict})
    def get(self, request, pk):
        return Response(judging.leaderboard(_problem(request, pk)))


class MyCodingSummaryView(APIView):
    permission_classes = [IsStudent]

    @extend_schema(responses={200: dict})
    def get(self, request):
        stats = judging.student_problem_stats(request.user)
        recent = CodeSubmission.objects.filter(student=request.user).select_related(
            "language", "student", "problem"
        )[:10]
        return Response(
            {
                "solved": sum(1 for s in stats.values() if s["solved"]),
                "attempted": len(stats),
                "submissions": CodeSubmission.objects.filter(student=request.user).count(),
                "recent": SubmissionRowSerializer(recent, many=True).data,
            }
        )
