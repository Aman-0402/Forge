from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AnnouncementViewSet,
    ContactMessagesAdminView,
    ContactMessageView,
    NotificationViewSet,
)

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("announcements", AnnouncementViewSet, basename="announcement")

urlpatterns = [
    path("contact/messages/", ContactMessagesAdminView.as_view(), name="contact-messages"),
    path("contact/", ContactMessageView.as_view(), name="contact-message"),
    *router.urls,
]
