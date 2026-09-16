"""Signed, expiring download links for private uploads.

Course content, assignment briefs and submissions are never served from public
``/media/``. Serializers only run after the API has checked access, and they return
``/api/v1/files/<signed-token>/<basename>`` links instead of raw storage URLs. The token
is a Django-signed storage name with a timestamp, so it cannot be forged or re-pointed,
and it stops working after ``FILE_LINK_MAX_AGE_SECONDS``. Links carry no user identity
so they work in ``<video>`` and ``<iframe>`` tags, which can't send a bearer token.

In production set ``PROTECTED_MEDIA_NGINX_PREFIX`` so Nginx streams the file (with Range
support) through ``X-Accel-Redirect`` from an ``internal`` location.
"""

import mimetypes
import posixpath

from django.conf import settings
from django.core import signing
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse
from django.urls import reverse
from django.views.static import serve
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

SALT = "forge.files"

# Folders safe to serve publicly (dev static serving only).
PUBLIC_MEDIA_PREFIXES = ("avatars/", "courses/thumbnails/")


class LinkExpired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This download link has expired. Reload the page to get a new one."
    default_code = "link_expired"


def sign_file_url(name, request=None):
    token = signing.dumps(name, salt=SALT, compress=True)
    path = reverse("signed-file", kwargs={"token": token, "filename": posixpath.basename(name)})
    return request.build_absolute_uri(path) if request is not None else path


class SignedFileField(serializers.FileField):
    """Accepts uploads like ``FileField``; renders a signed download link."""

    def to_representation(self, value):
        if not value:
            return None
        return sign_file_url(value.name, self.context.get("request"))


class SignedFileView(APIView):
    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]
    throttle_classes: list = []  # media players issue many range requests

    @extend_schema(responses={(200, "application/octet-stream"): bytes})
    def get(self, request, token, filename):
        try:
            name = signing.loads(token, salt=SALT, max_age=settings.FILE_LINK_MAX_AGE_SECONDS)
        except signing.SignatureExpired as exc:
            raise LinkExpired() from exc
        except signing.BadSignature as exc:
            raise Http404 from exc
        if (
            not isinstance(name, str)
            or posixpath.basename(name) != filename
            or ".." in name.split("/")
            or not default_storage.exists(name)
        ):
            raise Http404

        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        prefix = getattr(settings, "PROTECTED_MEDIA_NGINX_PREFIX", "")
        if prefix:
            response = HttpResponse(content_type=content_type)
            response["X-Accel-Redirect"] = f"{prefix.rstrip('/')}/{name}"
        else:
            response = FileResponse(default_storage.open(name, "rb"), content_type=content_type)
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        response["Cache-Control"] = f"private, max-age={settings.FILE_LINK_MAX_AGE_SECONDS}"
        response["X-Content-Type-Options"] = "nosniff"
        return response


def public_media(request, path):
    """Dev-only static serving that refuses private upload folders."""
    if not path.startswith(PUBLIC_MEDIA_PREFIXES) or ".." in path.split("/"):
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)
