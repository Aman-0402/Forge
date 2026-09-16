"""Admin-facing management endpoints (departments, users)."""

from django.db.models import Count
from rest_framework import viewsets

from apps.audit.mixins import AuditedModelMixin
from apps.core.permissions import IsAdminOrReadOnly

from .models import Department
from .serializers import DepartmentSerializer


class DepartmentViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = "department"
    search_fields = ["name", "code"]

    def get_queryset(self):
        return Department.objects.annotate(user_count=Count("users")).order_by("code")
