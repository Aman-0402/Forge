import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.courses.models import Chapter, ContentItem, Lesson, Module
from apps.courses.tests.factories import (
    ChapterFactory,
    ContentItemFactory,
    CourseFactory,
    EnrollmentFactory,
    LessonFactory,
    ModuleFactory,
)

API = "/api/v1"

pytestmark = pytest.mark.django_db


@pytest.fixture
def course(faculty_user):
    return CourseFactory(instructor=faculty_user)


@pytest.fixture
def manager(auth_client, faculty_user):
    return auth_client(faculty_user)


def pdf(name="notes.pdf", size=100):
    return SimpleUploadedFile(name, b"%PDF" + b"0" * size, content_type="application/pdf")


# ---------- create hierarchy ----------


def test_manager_builds_hierarchy_with_auto_order(manager, course):
    m1 = manager.post(f"{API}/courses/{course.pk}/modules/", {"title": "M1"}, format="json")
    m2 = manager.post(f"{API}/courses/{course.pk}/modules/", {"title": "M2"}, format="json")
    assert m1.status_code == 201, m1.data
    assert (m1.data["order"], m2.data["order"]) == (0, 1)

    ch = manager.post(f"{API}/modules/{m1.data['id']}/chapters/", {"title": "C1"}, format="json")
    assert ch.status_code == 201
    ls = manager.post(
        f"{API}/chapters/{ch.data['id']}/lessons/",
        {"title": "L1", "duration_minutes": 12, "is_preview": True},
        format="json",
    )
    assert ls.status_code == 201
    ct = manager.post(
        f"{API}/lessons/{ls.data['id']}/content/",
        {"kind": "text", "title": "Read me", "text": "Hello"},
        format="json",
    )
    assert ct.status_code == 201, ct.data
    assert AuditLog.objects.filter(action="content.create").exists()


def test_other_faculty_and_students_cannot_write(auth_client, course, student_user):
    url = f"{API}/courses/{course.pk}/modules/"
    other = UserFactory(role="faculty")
    assert auth_client(other).post(url, {"title": "x"}, format="json").status_code == 403
    assert auth_client(student_user).post(url, {"title": "x"}, format="json").status_code == 403
    module = ModuleFactory(course=course)
    detail = f"{API}/modules/{module.pk}/"
    assert auth_client(other).patch(detail, {"title": "y"}, format="json").status_code == 403
    assert auth_client(other).delete(detail).status_code == 403


def test_admin_can_write_any_course(auth_client, admin_user, course):
    res = auth_client(admin_user).post(
        f"{API}/courses/{course.pk}/modules/", {"title": "By admin"}, format="json"
    )
    assert res.status_code == 201


def test_parent_cannot_be_changed_by_patch(manager, course):
    lesson = LessonFactory(chapter=ChapterFactory(module=ModuleFactory(course=course)))
    other_chapter = ChapterFactory()
    manager.patch(f"{API}/lessons/{lesson.pk}/", {"chapter": other_chapter.pk}, format="json")
    lesson.refresh_from_db()
    assert lesson.chapter_id != other_chapter.pk


def test_delete_module_cascades(manager, course):
    module = ModuleFactory(course=course)
    lesson = LessonFactory(chapter=ChapterFactory(module=module))
    ContentItemFactory(lesson=lesson)
    assert manager.delete(f"{API}/modules/{module.pk}/").status_code == 204
    assert not Lesson.objects.exists() and not ContentItem.objects.exists()


# ---------- read access ----------


def test_student_reads_structure_of_published_course(auth_client, student_user, course):
    module = ModuleFactory(course=course)
    ChapterFactory(module=module)
    client = auth_client(student_user)
    assert client.get(f"{API}/courses/{course.pk}/modules/").status_code == 200
    assert len(client.get(f"{API}/modules/{module.pk}/chapters/").data) == 1


def test_draft_structure_hidden_from_students(auth_client, student_user):
    draft = CourseFactory(status="draft")
    module = ModuleFactory(course=draft)
    client = auth_client(student_user)
    assert client.get(f"{API}/courses/{draft.pk}/modules/").status_code == 404
    assert client.get(f"{API}/modules/{module.pk}/").status_code == 404


def test_content_locked_unless_enrolled_or_preview(auth_client, student_user, course):
    chapter = ChapterFactory(module=ModuleFactory(course=course))
    locked = LessonFactory(chapter=chapter)
    preview = LessonFactory(chapter=chapter, is_preview=True)
    item = ContentItemFactory(lesson=locked)
    ContentItemFactory(lesson=preview)
    client = auth_client(student_user)

    assert client.get(f"{API}/lessons/{locked.pk}/content/").status_code == 403
    assert client.get(f"{API}/content/{item.pk}/").status_code == 403
    assert client.get(f"{API}/lessons/{preview.pk}/content/").status_code == 200

    EnrollmentFactory(course=course, student=student_user)
    assert client.get(f"{API}/lessons/{locked.pk}/content/").status_code == 200
    assert client.get(f"{API}/content/{item.pk}/").status_code == 200


def test_dropped_enrollment_loses_content_access(auth_client, student_user, course):
    lesson = LessonFactory(chapter=ChapterFactory(module=ModuleFactory(course=course)))
    EnrollmentFactory(course=course, student=student_user, status="dropped")
    assert auth_client(student_user).get(f"{API}/lessons/{lesson.pk}/content/").status_code == 403


# ---------- reorder ----------


def test_reorder_modules(manager, course):
    a, b, c = (ModuleFactory(course=course) for _ in range(3))
    res = manager.post(
        f"{API}/courses/{course.pk}/modules/reorder/", {"ids": [c.pk, a.pk, b.pk]}, format="json"
    )
    assert res.status_code == 200
    assert list(Module.objects.filter(course=course).values_list("pk", flat=True)) == [
        c.pk,
        a.pk,
        b.pk,
    ]


def test_reorder_requires_exact_children(manager, course):
    a, b = ModuleFactory(course=course), ModuleFactory(course=course)
    foreign = ModuleFactory()
    url = f"{API}/courses/{course.pk}/modules/reorder/"
    assert manager.post(url, {"ids": [a.pk]}, format="json").status_code == 400
    assert manager.post(url, {"ids": [a.pk, b.pk, foreign.pk]}, format="json").status_code == 400


def test_reorder_lessons_and_content(manager, course):
    chapter = ChapterFactory(module=ModuleFactory(course=course))
    l1, l2 = LessonFactory(chapter=chapter), LessonFactory(chapter=chapter)
    res = manager.post(
        f"{API}/chapters/{chapter.pk}/lessons/reorder/", {"ids": [l2.pk, l1.pk]}, format="json"
    )
    assert res.status_code == 200
    assert list(Lesson.objects.filter(chapter=chapter).values_list("pk", flat=True)) == [
        l2.pk,
        l1.pk,
    ]
    i1, i2 = ContentItemFactory(lesson=l1), ContentItemFactory(lesson=l1)
    res = manager.post(
        f"{API}/lessons/{l1.pk}/content/reorder/", {"ids": [i2.pk, i1.pk]}, format="json"
    )
    assert res.status_code == 200
    assert Chapter.objects.count() == 1


# ---------- content validation ----------


@pytest.fixture
def lesson(course):
    return LessonFactory(chapter=ChapterFactory(module=ModuleFactory(course=course)))


def post_content(client, lesson, data, fmt="multipart"):
    return client.post(f"{API}/lessons/{lesson.pk}/content/", data, format=fmt)


def test_upload_pdf(manager, lesson):
    res = post_content(manager, lesson, {"kind": "pdf", "title": "Slides", "file": pdf()})
    assert res.status_code == 201, res.data
    assert res.data["file"].endswith(".pdf")
    assert "notes" not in res.data["file"]


@pytest.mark.parametrize(
    "data",
    [
        {"kind": "pdf", "title": "no file"},
        {"kind": "link", "title": "no url"},
        {"kind": "text", "title": "no text"},
    ],
)
def test_content_requires_payload_for_kind(manager, lesson, data):
    assert post_content(manager, lesson, data).status_code == 400


def test_rejects_wrong_extension(manager, lesson):
    bad = SimpleUploadedFile("virus.exe", b"MZ" * 10)
    res = post_content(manager, lesson, {"kind": "pdf", "title": "x", "file": bad})
    assert res.status_code == 400
    assert "file" in res.data["errors"]


def test_rejects_oversized_file(manager, lesson, settings):
    settings.CONTENT_UPLOAD_MAX_MB = {"default": 0.001, "video": 0.001}
    res = post_content(manager, lesson, {"kind": "pdf", "title": "x", "file": pdf(size=5000)})
    assert res.status_code == 400


def test_video_by_url_and_link(manager, lesson):
    video = {"kind": "video", "title": "Lecture", "url": "https://videos.example.com/1"}
    assert post_content(manager, lesson, video, "json").status_code == 201
    link = {"kind": "link", "title": "Docs", "url": "https://docs.python.org"}
    assert post_content(manager, lesson, link, "json").status_code == 201


# ---------- tree ----------


def build(course):
    m = ModuleFactory(course=course, title="M", order=0)
    c = ChapterFactory(module=m, title="C", order=0)
    free = LessonFactory(chapter=c, title="Free", order=0, is_preview=True)
    paid = LessonFactory(chapter=c, title="Paid", order=1)
    ContentItemFactory(lesson=free, title="free-item")
    ContentItemFactory(lesson=paid, title="paid-item")
    return free, paid


def lessons_of(tree):
    return tree["modules"][0]["chapters"][0]["lessons"]


def test_tree_for_unenrolled_student_locks_non_preview(auth_client, student_user, course):
    build(course)
    tree = auth_client(student_user).get(f"{API}/courses/{course.pk}/tree/").data
    assert tree["can_access_content"] is False
    free, paid = lessons_of(tree)
    assert (free["title"], free["locked"], len(free["contents"])) == ("Free", False, 1)
    assert (paid["title"], paid["locked"], paid["contents"]) == ("Paid", True, [])
    assert tree["lesson_count"] == 2


def test_tree_for_enrolled_student_and_manager_is_full(auth_client, student_user, manager, course):
    build(course)
    EnrollmentFactory(course=course, student=student_user)
    for client in (auth_client(student_user), manager):
        tree = client.get(f"{API}/courses/{course.pk}/tree/").data
        assert tree["can_access_content"] is True
        assert all(not lesson["locked"] for lesson in lessons_of(tree))
        assert lessons_of(tree)[1]["contents"][0]["title"] == "paid-item"


def test_tree_hidden_for_draft(auth_client, student_user):
    draft = CourseFactory(status="draft")
    assert auth_client(student_user).get(f"{API}/courses/{draft.pk}/tree/").status_code == 404
