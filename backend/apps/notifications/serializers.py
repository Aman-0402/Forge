from django.utils import timezone
from rest_framework import serializers

from .models import Announcement, Notification


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    department_code = serializers.CharField(source="department.code", read_only=True, default=None)
    published_at = serializers.DateTimeField(required=False)

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "body",
            "audience",
            "department",
            "department_code",
            "author",
            "author_name",
            "published_at",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author_name(self, obj) -> str | None:
        if not obj.author:
            return None
        return obj.author.get_full_name() or obj.author.email

    def validate(self, attrs):
        inst = self.instance
        audience = attrs.get("audience", inst.audience if inst else Announcement.Audience.ALL)
        department = attrs.get("department", inst.department if inst else None)

        if audience == Announcement.Audience.DEPARTMENT:
            if department is None:
                raise serializers.ValidationError({"department": ["Required for this audience."]})
        else:
            attrs["department"] = department = None

        published = attrs.get("published_at", inst.published_at if inst else timezone.now())
        expires = attrs.get("expires_at", inst.expires_at if inst else None)
        if expires and expires <= published:
            raise serializers.ValidationError({"expires_at": ["Must be after published_at."]})

        user = self.context["request"].user
        if user.role == "faculty":
            if audience != Announcement.Audience.DEPARTMENT:
                raise serializers.ValidationError(
                    {"audience": ["Faculty can only post to their department."]}
                )
            if not user.department_id or department.pk != user.department_id:
                raise serializers.ValidationError(
                    {"department": ["Faculty can only post to their own department."]}
                )
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "kind", "link", "is_read", "read_at", "created_at"]
        read_only_fields = fields
