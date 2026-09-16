from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import generics, mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.audit.mixins import AuditedModelMixin

from . import announcements, services
from .models import Announcement, Notification
from .serializers import AnnouncementSerializer, ContactMessageSerializer, NotificationSerializer

User = get_user_model()


class ContactMessageView(generics.CreateAPIView):
    """Public contact form. Saves the message and notifies every active admin."""

    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def perform_create(self, serializer):
        message = serializer.save()
        admins = User.objects.filter(role="admin", is_active=True)
        if admins:
            services.notify(
                admins,
                f"New contact message from {message.name}",
                f"{message.email}\n\n{message.message}",
                kind=Notification.Kind.INFO,
                email=True,
            )


class AnnouncementPermission(BasePermission):
    """Read: any authenticated user. Create: admin/faculty. Edit/delete: admin or author."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.method in SAFE_METHODS or request.user.role in ("admin", "faculty")

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.user.role == "admin":
            return True
        return obj.author_id == request.user.pk


class AnnouncementViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [AnnouncementPermission]
    audit_prefix = "announcement"
    filterset_fields = ["audience", "department", "course"]
    search_fields = ["title", "body"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Announcement.objects.none()
        return announcements.visible_announcements(self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        self._audit("create", serializer.instance, {"audience": serializer.instance.audience})
        announcements.deliver(serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        # A schedule moved to now (or earlier) goes out immediately; delivered posts never resend.
        announcements.deliver(serializer.instance)


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    filterset_fields = ["kind"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        qs = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get("unread") in ("1", "true", "True"):
            qs = qs.filter(is_read=False)
        return qs

    @extend_schema(parameters=[OpenApiParameter("unread", bool, description="Only unread")])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(request=None, responses=NotificationSerializer)
    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        return Response(self.get_serializer(services.mark_read(notification)).data)

    @extend_schema(
        request=None,
        responses=inline_serializer("ReadAll", {"updated": serializers.IntegerField()}),
    )
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        return Response({"updated": services.mark_all_read(request.user)})

    @extend_schema(
        responses=inline_serializer("UnreadCount", {"count": serializers.IntegerField()})
    )
    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"count": count})
