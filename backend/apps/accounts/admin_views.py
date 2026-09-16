"""Admin-facing management endpoints (departments, users)."""

from django.contrib.auth import get_user_model
from django.db.models import Count
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.audit.mixins import AuditedModelMixin
from apps.core.permissions import IsAdmin, IsAdminOrReadOnly

from . import user_admin
from .models import Department
from .serializers import AdminUserSerializer, DepartmentSerializer

User = get_user_model()


class DepartmentViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminOrReadOnly]
    audit_prefix = "department"
    search_fields = ["name", "code"]

    def get_queryset(self):
        return Department.objects.annotate(user_count=Count("users")).order_by("code")


class AdminUserCreatedSerializer(AdminUserSerializer):
    temp_password = serializers.CharField(
        allow_null=True, read_only=True, help_text="Set when no password was supplied."
    )

    class Meta(AdminUserSerializer.Meta):
        fields = [*AdminUserSerializer.Meta.fields, "temp_password"]


TempPasswordResponse = inline_serializer(
    "TempPassword", {"temp_password": serializers.CharField(allow_null=True)}
)


class UserAdminViewSet(viewsets.ModelViewSet):
    """Admin user management. DELETE deactivates; accounts are never hard-deleted."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ["role", "department", "is_active"]
    search_fields = [
        "email",
        "first_name",
        "last_name",
        "student_profile__roll_number",
        "faculty_profile__employee_id",
    ]
    ordering_fields = ["email", "first_name", "last_name", "date_joined", "last_login"]
    queryset = User.objects.select_related(
        "department", "student_profile", "faculty_profile"
    ).order_by("email")

    @extend_schema(request=AdminUserSerializer, responses={201: AdminUserCreatedSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, temp_password = user_admin.admin_create_user(
            actor=request.user, data=serializer.validated_data, request=request
        )
        data = dict(self.get_serializer(user).data)
        data["temp_password"] = temp_password
        return Response(data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        serializer.instance = user_admin.admin_update_user(
            actor=self.request.user,
            user=serializer.instance,
            data=serializer.validated_data,
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        user_admin.deactivate_user(actor=request.user, user=self.get_object(), request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses=TempPasswordResponse)
    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        temp = user_admin.reset_password(
            actor=request.user, user=self.get_object(), request=request
        )
        return Response({"temp_password": temp})

    @extend_schema(
        request={
            "multipart/form-data": inline_serializer(
                "BulkImportUpload", {"file": serializers.FileField()}
            )
        },
        responses=inline_serializer(
            "BulkImportResult",
            {
                "created": serializers.ListField(child=serializers.DictField()),
                "errors": serializers.ListField(child=serializers.DictField()),
            },
        ),
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def bulk_import(self, request):
        result = user_admin.bulk_import_users(
            actor=request.user, file=request.FILES.get("file"), request=request
        )
        return Response(result)
