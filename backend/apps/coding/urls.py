from django.urls import path
from rest_framework.routers import DefaultRouter

from . import judging_views as jv
from . import views

router = DefaultRouter()
router.register("problems", views.ProblemViewSet, basename="problem")

urlpatterns = [
    path("languages/", views.LanguageListView.as_view(), name="languages"),
    path(
        "problems/<int:pk>/testcases/", views.TestCaseListView.as_view(), name="problem-testcases"
    ),
    path(
        "problems/<int:pk>/testcases/import/",
        views.TestCaseImportView.as_view(),
        name="problem-testcases-import",
    ),
    path("testcases/<int:pk>/", views.TestCaseDetailView.as_view(), name="testcase-detail"),
    path("problems/<int:pk>/run/", jv.RunView.as_view(), name="problem-run"),
    path("problems/<int:pk>/submit/", jv.SubmitView.as_view(), name="problem-submit"),
    path(
        "problems/<int:pk>/submissions/",
        jv.ProblemSubmissionsView.as_view(),
        name="problem-submissions",
    ),
    path("problems/<int:pk>/rejudge/", jv.RejudgeView.as_view(), name="problem-rejudge"),
    path(
        "problems/<int:pk>/leaderboard/", jv.LeaderboardView.as_view(), name="problem-leaderboard"
    ),
    path(
        "code-submissions/<int:pk>/",
        jv.SubmissionDetailView.as_view(),
        name="code-submission-detail",
    ),
    path("me/coding/summary/", jv.MyCodingSummaryView.as_view(), name="my-coding-summary"),
    *router.urls,
]
