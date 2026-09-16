"""Full course outline in one response, with per-user locking and completion flags."""

from django.db.models import Prefetch

from .models import Chapter, Lesson, LessonProgress, Module
from .permissions import can_access_content, get_enrollment
from .structure_serializers import ContentItemSerializer


def build_tree(course, request):
    user = request.user
    full_access = can_access_content(user, course)
    enrollment = get_enrollment(user, course)
    completed = set()
    if enrollment:
        completed = set(
            LessonProgress.objects.filter(
                enrollment=enrollment, completed_at__isnull=False
            ).values_list("lesson_id", flat=True)
        )

    modules = Module.objects.filter(course=course).prefetch_related(
        Prefetch(
            "chapters",
            queryset=Chapter.objects.prefetch_related(
                Prefetch("lessons", queryset=Lesson.objects.prefetch_related("contents"))
            ),
        )
    )

    lesson_count = 0
    out_modules = []
    for module in modules:
        out_chapters = []
        for chapter in module.chapters.all():
            out_lessons = []
            for lesson in chapter.lessons.all():
                lesson_count += 1
                locked = not (full_access or lesson.is_preview)
                contents = (
                    []
                    if locked
                    else ContentItemSerializer(
                        lesson.contents.all(), many=True, context={"request": request}
                    ).data
                )
                out_lessons.append(
                    {
                        "id": lesson.pk,
                        "title": lesson.title,
                        "summary": lesson.summary,
                        "order": lesson.order,
                        "duration_minutes": lesson.duration_minutes,
                        "is_preview": lesson.is_preview,
                        "locked": locked,
                        "completed": lesson.pk in completed,
                        "contents": contents,
                    }
                )
            out_chapters.append(
                {
                    "id": chapter.pk,
                    "title": chapter.title,
                    "description": chapter.description,
                    "order": chapter.order,
                    "lessons": out_lessons,
                }
            )
        out_modules.append(
            {
                "id": module.pk,
                "title": module.title,
                "description": module.description,
                "order": module.order,
                "chapters": out_chapters,
            }
        )

    return {
        "course": course.pk,
        "title": course.title,
        "can_access_content": full_access,
        "is_enrolled": enrollment is not None,
        "progress_percent": enrollment.progress_percent if enrollment else None,
        "lesson_count": lesson_count,
        "completed_lesson_ids": sorted(completed),
        "modules": out_modules,
    }
