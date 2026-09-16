from django.urls import path
from rest_framework.routers import DefaultRouter

from . import attempt_views, bank_views, exam_views

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
    path("attempts/<int:pk>/", attempt_views.AttemptDetailView.as_view(), name="attempt-detail"),
    path(
        "attempts/<int:pk>/answers/<int:eq_pk>/",
        attempt_views.AnswerView.as_view(),
        name="attempt-answer",
    ),
    path(
        "attempts/<int:pk>/submit/",
        attempt_views.SubmitAttemptView.as_view(),
        name="attempt-submit",
    ),
    path(
        "attempts/<int:pk>/integrity-events/",
        attempt_views.IntegrityEventView.as_view(),
        name="attempt-integrity",
    ),
    *router.urls,
]
