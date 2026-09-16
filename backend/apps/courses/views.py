from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.audit.mixins import AuditedModelMixin
from apps.core.permissions import IsAdmin, IsAdminOrReadOnly

from . import services
from .models import Category, Course, Enrollment
from .permissions import (
    ACTIVE_ENROLLMENT,
    CanCreateCourse,
    IsCourseManagerOrReadOnly,
    can_manage_course,
)
from .serializers import CategorySerializer, CourseSerializer, RejectSerializer


class CategoryViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = "category"
    filterset_fields = ["kind", "parent"]
    search_fields = ["name"]


def visible_courses(user):
    qs = Course.objects.select_related("instructor", "department").prefetch_related(
        "co_instructors", "categories"
    )
    if user.role == "admin":
        return qs
    if user.role == "faculty":
        return qs.filter(
            Q(status=Course.Status.PUBLISHED) | Q(instructor=user) | Q(co_instructors=user)
        ).distinct()
    enrolled = Enrollment.objects.filter(student=user, status__in=ACTIVE_ENROLLMENT)
    return qs.filter(
        Q(status=Course.Status.PUBLISHED)
        | Q(status=Course.Status.ARCHIVED, pk__in=enrolled.values("course_id"))
    )


class CourseViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [CanCreateCourse, IsCourseManagerOrReadOnly]
    audit_prefix = "course"
    filterset_fields = ["status", "level", "categories", "department", "instructor"]
    search_fields = ["title", "code", "description"]
    ordering_fields = ["title", "created_at", "start_date"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Course.objects.none()
        lesson_ids = Count("modules__chapters__lessons", distinct=True)
        enrolled = Count(
            "enrollments",
            filter=Q(enrollments__status__in=ACTIVE_ENROLLMENT),
            distinct=True,
        )
        return (
            visible_courses(self.request.user)
            .annotate(lesson_count=lesson_ids, enrollment_count=enrolled)
            .order_by("-created_at", "-id")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated and user.role == "student":
            context["my_enrollments"] = {
                e.course_id: e
                for e in Enrollment.objects.filter(student=user, status__in=ACTIVE_ENROLLMENT)
            }
        return context

    def perform_destroy(self, instance):
        services.ensure_deletable(instance)
        super().perform_destroy(instance)

    # --- lifecycle actions ---

    def _manager_course(self):
        course = self.get_object()
        if not can_manage_course(self.request.user, course):
            raise PermissionDenied("Only the course instructors or an admin can do this.")
        return course

    def _respond(self, course):
        course = self.get_queryset().get(pk=course.pk)
        return Response(self.get_serializer(course).data)

    @extend_schema(request=None, responses=CourseSerializer)
    @action(detail=True, methods=["post"], url_path="submit-for-approval")
    def submit_for_approval(self, request, pk=None):
        course = services.submit_for_approval(
            actor=request.user, course=self._manager_course(), request=request
        )
        return self._respond(course)

    @extend_schema(request=None, responses=CourseSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        course = services.approve(actor=request.user, course=self.get_object(), request=request)
        return self._respond(course)

    @extend_schema(request=RejectSerializer, responses=CourseSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def reject(self, request, pk=None):
        data = RejectSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        course = services.reject(
            actor=request.user,
            course=self.get_object(),
            reason=data.validated_data["reason"],
            request=request,
        )
        return self._respond(course)

    @extend_schema(request=None, responses=CourseSerializer)
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        course = services.archive(
            actor=request.user, course=self._manager_course(), request=request
        )
        return self._respond(course)

    @extend_schema(responses={200: dict})
    @action(detail=True, methods=["get"])
    def tree(self, request, pk=None):
        from .tree import build_tree

        return Response(build_tree(self.get_object(), request))

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        course = self.get_queryset().get(pk=response.data["id"])
        return Response(self.get_serializer(course).data, status=status.HTTP_201_CREATED)
