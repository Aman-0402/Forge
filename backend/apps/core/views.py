from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, viewsets
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.mixins import AuditedModelMixin
from apps.audit.services import log_action

from . import reports
from .models import MarketingStat, SiteSettings
from .permissions import IsAdmin
from .serializers import (
    MarketingStatSerializer,
    ReportsOverviewSerializer,
    SiteSettingsSerializer,
    TimeseriesSerializer,
)


class _IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "admin")


class PublicReadAdminWrite(BasePermission):
    """Anyone may read; only admins may write. Unlike core.permissions.IsAdminOrReadOnly,
    reads don't require authentication — this is for public marketing content."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class SiteSettingsView(APIView):
    """GET: anyone. PATCH: admins only. Always the one singleton row."""

    serializer_class = SiteSettingsSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [_IsAdmin()]

    @extend_schema(responses=SiteSettingsSerializer)
    def get(self, request):
        return Response(SiteSettingsSerializer(SiteSettings.current()).data)

    @extend_schema(request=SiteSettingsSerializer, responses=SiteSettingsSerializer)
    def patch(self, request):
        instance = SiteSettings.current()
        serializer = SiteSettingsSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(
            request.user,
            "site_settings.update",
            target=instance,
            metadata={"fields": sorted(request.data.keys())},
            request=request,
        )
        return Response(serializer.data)


class MarketingStatViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    queryset = MarketingStat.objects.all()
    serializer_class = MarketingStatSerializer
    permission_classes = [PublicReadAdminWrite]
    audit_prefix = "marketing_stat"
    pagination_class = None


class ReportsOverviewView(APIView):
    """Aggregate counts for the admin analytics dashboard."""

    permission_classes = [IsAdmin]

    @extend_schema(responses=ReportsOverviewSerializer)
    def get(self, request):
        return Response(ReportsOverviewSerializer(reports.overview()).data)


class ReportsTimeseriesView(APIView):
    """Daily activity counts for the analytics dashboard's trend line chart.

    ?days=N (1-180, default 30) filters the window; anything unparsable falls
    back to the default rather than 400ing over what's just a display filter.
    """

    permission_classes = [IsAdmin]

    @extend_schema(
        parameters=[OpenApiParameter("days", int, description="1-180, default 30")],
        responses=TimeseriesSerializer,
    )
    def get(self, request):
        data = reports.timeseries(request.query_params.get("days"))
        return Response(TimeseriesSerializer(data).data)
