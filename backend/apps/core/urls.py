from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("marketing-stats", views.MarketingStatViewSet, basename="marketing-stat")

urlpatterns = [
    path("site-settings/", views.SiteSettingsView.as_view(), name="site-settings"),
    path("reports/overview/", views.ReportsOverviewView.as_view(), name="reports-overview"),
    *router.urls,
]
