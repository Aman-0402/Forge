from pathlib import Path

from django.conf import settings
from rest_framework import serializers

CONTENT_EXTENSIONS = {
    "video": {".mp4", ".webm", ".mov", ".mkv", ".m4v"},
    "pdf": {".pdf"},
    "ppt": {".ppt", ".pptx", ".odp"},
    "doc": {".doc", ".docx", ".odt", ".rtf", ".txt", ".md"},
}

ASSIGNMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".odt", ".txt", ".md", ".rtf",
    ".ppt", ".pptx", ".xls", ".xlsx", ".csv",
    ".zip", ".png", ".jpg", ".jpeg",
    ".py", ".java", ".c", ".cpp", ".h", ".js", ".ts", ".ipynb", ".sql",
}  # fmt: skip


def content_max_mb(kind):
    limits = getattr(settings, "CONTENT_UPLOAD_MAX_MB", {})
    return limits.get(kind, limits.get("default", 50))


def validate_upload(file, allowed_extensions, max_mb):
    ext = Path(file.name).suffix.lower()
    if ext not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))
        raise serializers.ValidationError(
            f"File type '{ext or 'none'}' not allowed. Use: {allowed}."
        )
    if file.size > max_mb * 1024 * 1024:
        raise serializers.ValidationError(f"File too large (max {max_mb:g} MB).")
    return file
