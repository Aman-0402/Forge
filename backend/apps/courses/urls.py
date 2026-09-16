from django.urls import path
from rest_framework.routers import DefaultRouter

from . import assignment_views as av
from . import enrollment_views as ev
from . import progress_views as pv
from . import structure_views as sv
from . import views

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("courses", views.CourseViewSet, basename="course")
router.register("enrollments", ev.EnrollmentViewSet, basename="enrollment")

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
    path("me/enrollments/", ev.MyEnrollmentsView.as_view(), name="my-enrollments"),
    path(
        "courses/<int:pk>/assignments/",
        av.CourseAssignmentsView.as_view(),
        name="course-assignments",
    ),
    path("assignments/<int:pk>/", av.AssignmentDetailView.as_view(), name="assignment-detail"),
    path(
        "assignments/<int:pk>/submit/", av.SubmitAssignmentView.as_view(), name="assignment-submit"
    ),
    path(
        "assignments/<int:pk>/submissions/",
        av.AssignmentSubmissionsView.as_view(),
        name="assignment-submissions",
    ),
    path("submissions/<int:pk>/", av.SubmissionDetailView.as_view(), name="submission-detail"),
    path("submissions/<int:pk>/grade/", av.GradeSubmissionView.as_view(), name="submission-grade"),
    *nested("courses", "course_pk", "modules", sv.ModuleViewSet, "module"),
    path("modules/<int:pk>/", sv.ModuleViewSet.as_view(DETAIL), name="module-detail"),
    *nested("modules", "module_pk", "chapters", sv.ChapterViewSet, "chapter"),
    path("chapters/<int:pk>/", sv.ChapterViewSet.as_view(DETAIL), name="chapter-detail"),
    *nested("chapters", "chapter_pk", "lessons", sv.LessonViewSet, "lesson"),
    path("lessons/<int:pk>/", sv.LessonViewSet.as_view(DETAIL), name="lesson-detail"),
    path("lessons/<int:pk>/complete/", pv.CompleteLessonView.as_view(), name="lesson-complete"),
    path("lessons/<int:pk>/position/", pv.LessonPositionView.as_view(), name="lesson-position"),
    *nested("lessons", "lesson_pk", "content", sv.ContentItemViewSet, "content"),
    path("content/<int:pk>/", sv.ContentItemViewSet.as_view(DETAIL), name="content-detail"),
    *router.urls,
]
