from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_action

from . import assignments as services
from .assignment_serializers import (
    AssignmentSerializer,
    GradeSerializer,
    SubmissionSerializer,
    SubmitSerializer,
)
from .models import Assignment, AssignmentSubmission, Course
from .permissions import can_access_content, can_manage_course
from .views import visible_courses

PARSERS = [JSONParser, MultiPartParser, FormParser]


def _visible_course(request, pk):
    return get_object_or_404(visible_courses(request.user), pk=pk)


def _require_access(user, course):
    if not can_access_content(user, course):
        raise PermissionDenied("Enroll in this course to see its assignments.")


def _require_manager(user, course):
    if not can_manage_course(user, course):
        raise PermissionDenied("Only the course instructors or an admin can do this.")


def _assignment(request, pk):
    assignment = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    _visible_course(request, assignment.course_id)
    return assignment


class CourseAssignmentsView(APIView):
    parser_classes = PARSERS

    def _course(self, request, pk) -> Course:
        return _visible_course(request, pk)

    @extend_schema(responses=AssignmentSerializer(many=True))
    def get(self, request, pk):
        course = self._course(request, pk)
        _require_access(request.user, course)
        qs = Assignment.objects.filter(course=course)
        context = {"request": request}
        if can_manage_course(request.user, course):
            qs = qs.annotate(
                submission_count=Count("submissions", distinct=True),
                graded_count=Count(
                    "submissions", filter=Q(submissions__graded_at__isnull=False), distinct=True
                ),
            )
        else:
            context["my_submissions"] = {
                s.assignment_id: s
                for s in AssignmentSubmission.objects.filter(
                    student=request.user, assignment__course=course
                )
            }
        return Response(AssignmentSerializer(qs, many=True, context=context).data)

    @extend_schema(request=AssignmentSerializer, responses={201: AssignmentSerializer})
    def post(self, request, pk):
        course = self._course(request, pk)
        _require_manager(request.user, course)
        serializer = AssignmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(course=course, created_by=request.user)
        log_action(request.user, "assignment.create", target=assignment, request=request)
        services.notify_new_assignment(assignment)
        return Response(
            AssignmentSerializer(assignment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AssignmentDetailView(APIView):
    parser_classes = PARSERS

    @extend_schema(responses=AssignmentSerializer)
    def get(self, request, pk):
        assignment = _assignment(request, pk)
        _require_access(request.user, assignment.course)
        return Response(AssignmentSerializer(assignment, context={"request": request}).data)

    @extend_schema(request=AssignmentSerializer, responses=AssignmentSerializer)
    def patch(self, request, pk):
        assignment = _assignment(request, pk)
        _require_manager(request.user, assignment.course)
        serializer = AssignmentSerializer(
            assignment, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            request.user,
            "assignment.update",
            target=assignment,
            metadata={"fields": sorted(serializer.validated_data)},
            request=request,
        )
        return Response(serializer.data)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        assignment = _assignment(request, pk)
        _require_manager(request.user, assignment.course)
        log_action(request.user, "assignment.delete", target=assignment, request=request)
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubmitAssignmentView(APIView):
    parser_classes = PARSERS

    @extend_schema(
        request=SubmitSerializer, responses={200: SubmissionSerializer, 201: SubmissionSerializer}
    )
    def post(self, request, pk):
        assignment = _assignment(request, pk)
        data = SubmitSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        submission, created = services.submit(
            actor=request.user,
            assignment=assignment,
            file=data.validated_data.get("file"),
            text=data.validated_data.get("text", ""),
            request=request,
        )
        return Response(
            SubmissionSerializer(submission, context={"request": request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class AssignmentSubmissionsView(generics.ListAPIView):
    """Managers see every submission; students see only their own."""

    serializer_class = SubmissionSerializer

    @extend_schema(parameters=[OpenApiParameter("graded", bool)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AssignmentSubmission.objects.none()
        assignment = _assignment(self.request, self.kwargs["pk"])
        user = self.request.user
        qs = AssignmentSubmission.objects.filter(assignment=assignment).select_related(
            "assignment", "student__student_profile"
        )
        if not can_manage_course(user, assignment.course):
            _require_access(user, assignment.course)
            qs = qs.filter(student=user)
        graded = self.request.query_params.get("graded")
        if graded in ("true", "1"):
            qs = qs.filter(graded_at__isnull=False)
        elif graded in ("false", "0"):
            qs = qs.filter(graded_at__isnull=True)
        return qs


def _submission(request, pk):
    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related("assignment__course", "student"), pk=pk
    )
    _visible_course(request, submission.assignment.course_id)
    return submission


class SubmissionDetailView(APIView):
    @extend_schema(responses=SubmissionSerializer)
    def get(self, request, pk):
        submission = _submission(request, pk)
        course = submission.assignment.course
        if submission.student_id != request.user.pk:
            _require_manager(request.user, course)
        return Response(SubmissionSerializer(submission, context={"request": request}).data)


class GradeSubmissionView(APIView):
    @extend_schema(request=GradeSerializer, responses=SubmissionSerializer)
    def post(self, request, pk):
        submission = _submission(request, pk)
        _require_manager(request.user, submission.assignment.course)
        data = GradeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        submission = services.grade(
            actor=request.user, submission=submission, request=request, **data.validated_data
        )
        return Response(SubmissionSerializer(submission, context={"request": request}).data)
