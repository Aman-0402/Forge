from django.urls import path
from rest_framework.routers import DefaultRouter

from . import bank_views, exam_views

router = DefaultRouter()
router.register("question-banks", bank_views.QuestionBankViewSet, basename="question-bank")
router.register("exams", exam_views.ExamViewSet, basename="exam")

urlpatterns = [
    path(
        "question-banks/<int:pk>/questions/",
        bank_views.BankQuestionsView.as_view(),
        name="bank-questions",
    ),
    path("questions/<int:pk>/", bank_views.QuestionDetailView.as_view(), name="question-detail"),
    path(
        "exams/<int:pk>/questions/", exam_views.ExamQuestionsView.as_view(), name="exam-questions"
    ),
    path(
        "exams/<int:pk>/questions/<int:eq_pk>/",
        exam_views.ExamQuestionDetailView.as_view(),
        name="exam-question-detail",
    ),
    *router.urls,
]
