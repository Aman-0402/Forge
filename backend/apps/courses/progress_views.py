from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from . import progress
from .enrollment_serializers import EnrollmentSerializer
from .models import Lesson
from .views import visible_courses


def _visible_lesson(request, pk):
    lesson = get_object_or_404(Lesson.objects.select_related("chapter__module__course"), pk=pk)
    course = lesson.chapter.module.course
    get_object_or_404(visible_courses(request.user), pk=course.pk)
    return lesson


class CompleteLessonView(APIView):
    @extend_schema(request=None, responses=EnrollmentSerializer)
    def post(self, request, pk):
        enrollment = progress.complete_lesson(
            actor=request.user, lesson=_visible_lesson(request, pk), request=request
        )
        return Response(EnrollmentSerializer(enrollment, context={"request": request}).data)


class PositionSerializer(serializers.Serializer):
    seconds = serializers.IntegerField(min_value=0)


class LessonPositionView(APIView):
    @extend_schema(
        request=PositionSerializer,
        responses=inline_serializer(
            "LessonPosition",
            {"lesson": serializers.IntegerField(), "seconds": serializers.IntegerField()},
        ),
    )
    def post(self, request, pk):
        lesson = _visible_lesson(request, pk)
        data = PositionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        record = progress.save_position(
            actor=request.user, lesson=lesson, seconds=data.validated_data["seconds"]
        )
        return Response({"lesson": lesson.pk, "seconds": record.last_position_seconds})
