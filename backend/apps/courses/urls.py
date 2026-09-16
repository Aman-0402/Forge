from django.urls import path
from rest_framework.routers import DefaultRouter

from . import structure_views as sv
from . import views

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("courses", views.CourseViewSet, basename="course")

LIST = {"get": "list", "post": "create"}
DETAIL = {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
REORDER = {"post": "reorder"}


def nested(prefix, parent_kwarg, child, viewset, name):
    return [
        path(f"{prefix}/<int:{parent_kwarg}>/{child}/", viewset.as_view(LIST), name=f"{name}-list"),
        path(
            f"{prefix}/<int:{parent_kwarg}>/{child}/reorder/",
            viewset.as_view(REORDER),
            name=f"{name}-reorder",
        ),
    ]


urlpatterns = [
    *nested("courses", "course_pk", "modules", sv.ModuleViewSet, "module"),
    path("modules/<int:pk>/", sv.ModuleViewSet.as_view(DETAIL), name="module-detail"),
    *nested("modules", "module_pk", "chapters", sv.ChapterViewSet, "chapter"),
    path("chapters/<int:pk>/", sv.ChapterViewSet.as_view(DETAIL), name="chapter-detail"),
    *nested("chapters", "chapter_pk", "lessons", sv.LessonViewSet, "lesson"),
    path("lessons/<int:pk>/", sv.LessonViewSet.as_view(DETAIL), name="lesson-detail"),
    *nested("lessons", "lesson_pk", "content", sv.ContentItemViewSet, "content"),
    path("content/<int:pk>/", sv.ContentItemViewSet.as_view(DETAIL), name="content-detail"),
    *router.urls,
]
