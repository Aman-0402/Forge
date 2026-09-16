from django.urls import path
from rest_framework.routers import DefaultRouter

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
    *router.urls,
]
