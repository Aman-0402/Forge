"""Nested course structure: modules -> chapters -> lessons -> content items.

List/create/reorder live under the parent (``courses/{id}/modules/``); retrieve/update/delete
use a flat path (``modules/{id}/``). Every request resolves the owning course and applies
the same rules: hidden course -> 404, writes need a course manager, lesson content needs
enrollment or a preview lesson.
"""

from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from apps.audit.mixins import AuditedModelMixin

from .models import Chapter, ContentItem, Course, Lesson, Module
from .permissions import can_access_content, can_manage_course
from .structure_serializers import (
    ChapterSerializer,
    ContentItemSerializer,
    LessonSerializer,
    ModuleSerializer,
    ReorderSerializer,
)
from .views import visible_courses


def course_of(obj):
    if isinstance(obj, Course):
        return obj
    if isinstance(obj, Module):
        return obj.course
    if isinstance(obj, Chapter):
        return obj.module.course
    if isinstance(obj, Lesson):
        return obj.chapter.module.course
    if isinstance(obj, ContentItem):
        return obj.lesson.chapter.module.course
    raise TypeError(obj)


class CourseChildViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    model = None
    parent_model = None
    parent_kwarg = ""
    parent_field = ""
    select_path = ""

    # --- resolution & rules ---

    def get_parent(self):
        if not hasattr(self, "_parent"):
            parent = get_object_or_404(self.parent_model, pk=self.kwargs[self.parent_kwarg])
            self._check_course(course_of(parent), parent)
            self._parent = parent
        return self._parent

    def _check_course(self, course, node):
        user = self.request.user
        if not visible_courses(user).filter(pk=course.pk).exists():
            raise NotFound()
        if self.request.method not in SAFE_METHODS and not can_manage_course(user, course):
            raise PermissionDenied("Only the course instructors or an admin can change this.")
        self.check_content_access(course, node)

    def check_content_access(self, course, node):
        """Hook for content items; structure itself is readable by anyone who sees the course."""

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.model.objects.none()
        qs = (
            self.model.objects.select_related(self.select_path)
            if self.select_path
            else (self.model.objects.all())
        )
        if self.parent_kwarg in self.kwargs:
            qs = qs.filter(**{self.parent_field: self.get_parent()})
        return qs

    def get_object(self):
        obj = super().get_object()
        self._check_course(course_of(obj), obj)
        return obj

    def list(self, request, *args, **kwargs):
        self.get_parent()
        return super().list(request, *args, **kwargs)

    def paginate_queryset(self, queryset):
        return None  # children are small ordered lists

    def perform_create(self, serializer):
        parent = self.get_parent()
        extra = {self.parent_field: parent}
        if "order" not in serializer.validated_data:
            current = self.model.objects.filter(**extra).aggregate(m=Max("order"))["m"]
            extra["order"] = 0 if current is None else current + 1
        serializer.save(**extra)
        self._audit("create", serializer.instance)

    @extend_schema(request=ReorderSerializer, responses={200: None})
    @action(detail=False, methods=["post"])
    def reorder(self, request, *args, **kwargs):
        parent = self.get_parent()
        data = ReorderSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ids = data.validated_data["ids"]
        children = self.model.objects.filter(**{self.parent_field: parent})
        existing = set(children.values_list("pk", flat=True))
        if len(ids) != len(set(ids)) or set(ids) != existing:
            raise ValidationError({"ids": ["Must list every child of this parent exactly once."]})
        with transaction.atomic():
            for index, pk in enumerate(ids):
                children.filter(pk=pk).update(order=index)
        self._audit("reorder", parent, {"ids": ids})
        return Response({"ids": ids}, status=status.HTTP_200_OK)


class ModuleViewSet(CourseChildViewSet):
    model = Module
    parent_model = Course
    parent_kwarg = "course_pk"
    parent_field = "course"
    select_path = "course"
    serializer_class = ModuleSerializer
    audit_prefix = "module"


class ChapterViewSet(CourseChildViewSet):
    model = Chapter
    parent_model = Module
    parent_kwarg = "module_pk"
    parent_field = "module"
    select_path = "module__course"
    serializer_class = ChapterSerializer
    audit_prefix = "chapter"


class LessonViewSet(CourseChildViewSet):
    model = Lesson
    parent_model = Chapter
    parent_kwarg = "chapter_pk"
    parent_field = "chapter"
    select_path = "chapter__module__course"
    serializer_class = LessonSerializer
    audit_prefix = "lesson"

    def perform_create(self, serializer):
        super().perform_create(serializer)
        from .progress import recompute_course_progress

        recompute_course_progress(course_of(serializer.instance))

    def perform_destroy(self, instance):
        course = course_of(instance)
        super().perform_destroy(instance)
        from .progress import recompute_course_progress

        recompute_course_progress(course)


class ContentItemViewSet(CourseChildViewSet):
    model = ContentItem
    parent_model = Lesson
    parent_kwarg = "lesson_pk"
    parent_field = "lesson"
    select_path = "lesson__chapter__module__course"
    serializer_class = ContentItemSerializer
    audit_prefix = "content"
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def check_content_access(self, course, node):
        lesson = node if isinstance(node, Lesson) else node.lesson
        if lesson.is_preview or can_access_content(self.request.user, course):
            return
        raise PermissionDenied("Enroll in this course to open its lessons.")
