from urllib.parse import urlparse

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import RequestFactory
from freezegun import freeze_time

from apps.core.files import public_media, sign_file_url
from apps.courses.tests.factories import (
    ChapterFactory,
    ContentItemFactory,
    CourseFactory,
    EnrollmentFactory,
    LessonFactory,
    ModuleFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def stored():
    return default_storage.save("courses/content/abc123.pdf", ContentFile(b"%PDF-secret"))


def path_of(url):
    return urlparse(url).path


def test_signed_link_downloads_without_auth(api_client, stored):
    url = sign_file_url(stored)
    assert path_of(url).startswith("/api/v1/files/") and url.endswith("/abc123.pdf")
    res = api_client.get(path_of(url))
    assert res.status_code == 200
    assert b"".join(res.streaming_content) == b"%PDF-secret"
    assert res["Cache-Control"].startswith("private")
    assert res["X-Content-Type-Options"] == "nosniff"


def test_tampered_link_rejected(api_client, stored):
    path = path_of(sign_file_url(stored))
    token = path.split("/")[4]
    assert api_client.get(path.replace(token, token[:-2] + "xx")).status_code == 404
    other = default_storage.save("courses/submissions/zzz.pdf", ContentFile(b"x"))
    assert api_client.get(path.replace("abc123.pdf", other.split("/")[-1])).status_code == 404


def test_expired_link_rejected(api_client, stored, settings):
    settings.FILE_LINK_MAX_AGE_SECONDS = 60
    with freeze_time("2026-09-16 10:00:00") as frozen:
        path = path_of(sign_file_url(stored))
        frozen.tick(61)
        res = api_client.get(path)
    assert res.status_code == 403 and res.data["code"] == "link_expired"


def test_missing_file_is_404(api_client):
    assert api_client.get(path_of(sign_file_url("courses/content/gone.pdf"))).status_code == 404


def test_nginx_mode_hands_off_with_accel_redirect(api_client, stored, settings):
    settings.PROTECTED_MEDIA_NGINX_PREFIX = "/protected-media/"
    res = api_client.get(path_of(sign_file_url(stored)))
    assert res.status_code == 200
    assert res["X-Accel-Redirect"] == f"/protected-media/{stored}"


def test_public_media_serves_only_public_folders(stored):
    rf = RequestFactory()
    default_storage.save("avatars/me.png", ContentFile(b"png"))
    assert public_media(rf.get("/media/avatars/me.png"), "avatars/me.png").status_code == 200
    from django.http import Http404

    with pytest.raises(Http404):
        public_media(rf.get(f"/media/{stored}"), stored)


def test_course_tree_returns_signed_file_links(auth_client, student_user, faculty_user):
    course = CourseFactory(instructor=faculty_user, status="published")
    lesson = LessonFactory(chapter=ChapterFactory(module=ModuleFactory(course=course)))
    item = ContentItemFactory(lesson=lesson, kind="pdf", text="", url="")
    item.file.save("slides.pdf", ContentFile(b"%PDF"), save=True)
    EnrollmentFactory(course=course, student=student_user)

    res = auth_client(student_user).get(f"/api/v1/courses/{course.pk}/tree/")
    assert res.status_code == 200, res.data
    text = res.content.decode()
    assert "/api/v1/files/" in text
    assert "/media/courses/content/" not in text
