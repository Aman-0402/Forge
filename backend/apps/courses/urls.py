from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("courses", views.CourseViewSet, basename="course")

urlpatterns = [*router.urls]
