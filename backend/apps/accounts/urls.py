from django.urls import path
from rest_framework.routers import DefaultRouter

from . import admin_views, views

router = DefaultRouter()
router.register("departments", admin_views.DepartmentViewSet, basename="department")

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/token/", views.LoginView.as_view(), name="auth-token"),
    path("auth/token/refresh/", views.RefreshView.as_view(), name="auth-token-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="auth-change-password"),
    *router.urls,
]
