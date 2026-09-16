from rest_framework.routers import DefaultRouter

from .views import AnnouncementViewSet, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("announcements", AnnouncementViewSet, basename="announcement")

urlpatterns = router.urls
