from rest_framework import serializers

from .models import Chapter, ContentItem, Lesson, Module
from .validators import CONTENT_EXTENSIONS, content_max_mb, validate_upload

FILE_KINDS = set(CONTENT_EXTENSIONS)


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["id", "course", "title", "description", "order", "created_at", "updated_at"]
        read_only_fields = ["course", "created_at", "updated_at"]
        extra_kwargs = {"order": {"required": False}}


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "module", "title", "description", "order", "created_at", "updated_at"]
        read_only_fields = ["module", "created_at", "updated_at"]
        extra_kwargs = {"order": {"required": False}}


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            "id",
            "chapter",
            "title",
            "summary",
            "order",
            "duration_minutes",
            "is_preview",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["chapter", "created_at", "updated_at"]
        extra_kwargs = {"order": {"required": False}}


class ContentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentItem
        fields = [
            "id",
            "lesson",
            "kind",
            "title",
            "file",
            "url",
            "text",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["lesson", "created_at", "updated_at"]
        extra_kwargs = {"order": {"required": False}}

    def validate(self, attrs):
        inst = self.instance
        kind = attrs.get("kind", getattr(inst, "kind", None))
        file = attrs.get("file", getattr(inst, "file", None))
        url = attrs.get("url", getattr(inst, "url", ""))
        text = attrs.get("text", getattr(inst, "text", ""))

        if "file" in attrs and attrs["file"] and kind in FILE_KINDS:
            try:
                validate_upload(attrs["file"], CONTENT_EXTENSIONS[kind], content_max_mb(kind))
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"file": exc.detail}) from exc

        if kind == ContentItem.Kind.LINK and not url:
            raise serializers.ValidationError({"url": ["Required for links."]})
        if kind == ContentItem.Kind.TEXT and not text:
            raise serializers.ValidationError({"text": ["Required for text content."]})
        if kind == ContentItem.Kind.VIDEO and not (file or url):
            raise serializers.ValidationError({"file": ["Upload a video file or give a url."]})
        if kind in FILE_KINDS - {ContentItem.Kind.VIDEO} and not file:
            raise serializers.ValidationError({"file": [f"A file is required for {kind}."]})
        if "file" in attrs and attrs["file"] and kind not in FILE_KINDS:
            raise serializers.ValidationError({"file": [f"'{kind}' content cannot have a file."]})
        return attrs


class ReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
