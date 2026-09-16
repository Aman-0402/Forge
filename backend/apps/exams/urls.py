from django.urls import path
from rest_framework.routers import DefaultRouter

from . import bank_views

router = DefaultRouter()
router.register("question-banks", bank_views.QuestionBankViewSet, basename="question-bank")

urlpatterns = [
    path(
        "question-banks/<int:pk>/questions/",
        bank_views.BankQuestionsView.as_view(),
        name="bank-questions",
    ),
    path("questions/<int:pk>/", bank_views.QuestionDetailView.as_view(), name="question-detail"),
    *router.urls,
]
