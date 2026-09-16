import pytest

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.courses.models import Enrollment, LessonProgress
from apps.courses.tests.factories import (
    ChapterFactory,
    CourseFactory,
    EnrollmentFactory,
    LessonFactory,
    ModuleFactory,
)
from apps.notifications.models import Notification

API = "/api/v1"

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(faculty_user, student_user):
    course = CourseFactory(instructor=faculty_user)
    chapter = ChapterFactory(module=ModuleFactory(course=course))
    lessons = [LessonFactory(chapter=chapter) for _ in range(4)]
    enrollment = EnrollmentFactory(course=course, student=student_user)
    return course, chapter, lessons, enrollment


def complete(client, lesson):
    return client.post(f"{API}/lessons/{lesson.pk}/complete/")


def test_completing_lessons_updates_percent(auth_client, student_user, setup):
    course, _, lessons, enrollment = setup
    client = auth_client(student_user)
    res = complete(client, lessons[0])
    assert res.status_code == 200, res.data
    assert res.data["progress_percent"] == 25
    assert complete(client, lessons[0]).data["progress_percent"] == 25
    assert LessonProgress.objects.filter(enrollment=enrollment).count() == 1


def test_completing_all_lessons_completes_course(auth_client, student_user, setup):
    course, _, lessons, enrollment = setup
    client = auth_client(student_user)
    for lesson in lessons:
        res = complete(client, lesson)
    assert res.data["progress_percent"] == 100
    assert res.data["status"] == "completed"
    enrollment.refresh_from_db()
    assert enrollment.completed_at is not None
    assert Notification.objects.filter(
        recipient=student_user, title__startswith="Completed"
    ).exists()
    assert AuditLog.objects.filter(action="enrollment.complete").exists()


def test_unenrolled_dropped_and_faculty_cannot_complete(auth_client, faculty_user, setup):
    course, _, lessons, enrollment = setup
    stranger = UserFactory(role="student")
    preview = LessonFactory(chapter=lessons[0].chapter, is_preview=True)
    assert complete(auth_client(stranger), lessons[0]).status_code == 403
    assert complete(auth_client(stranger), preview).status_code == 403
    assert complete(auth_client(faculty_user), lessons[0]).status_code == 403
    Enrollment.objects.filter(pk=enrollment.pk).update(status="dropped")
    assert complete(auth_client(enrollment.student), lessons[0]).status_code == 403


def test_hidden_course_lesson_is_not_found(auth_client, student_user):
    draft = CourseFactory(status="draft")
    lesson = LessonFactory(chapter=ChapterFactory(module=ModuleFactory(course=draft)))
    assert complete(auth_client(student_user), lesson).status_code == 404


def test_save_video_position(auth_client, student_user, setup):
    _, _, lessons, enrollment = setup
    client = auth_client(student_user)
    url = f"{API}/lessons/{lessons[1].pk}/position/"
    assert client.post(url, {"seconds": 95}, format="json").status_code == 200
    progress = LessonProgress.objects.get(enrollment=enrollment, lesson=lessons[1])
    assert progress.last_position_seconds == 95 and progress.completed_at is None
    assert client.post(url, {"seconds": -3}, format="json").status_code == 400


def test_my_progress(auth_client, student_user, setup):
    course, _, lessons, _ = setup
    client = auth_client(student_user)
    complete(client, lessons[2])
    res = client.get(f"{API}/courses/{course.pk}/progress/me/")
    assert res.status_code == 200
    assert res.data["progress_percent"] == 25
    assert res.data["completed_lesson_ids"] == [lessons[2].pk]
    assert res.data["total_lessons"] == 4


def test_my_progress_requires_enrollment(auth_client, setup):
    course = setup[0]
    stranger = UserFactory(role="student")
    assert auth_client(stranger).get(f"{API}/courses/{course.pk}/progress/me/").status_code == 403


def test_manager_progress_table(auth_client, faculty_user, student_user, setup):
    course, _, lessons, _ = setup
    complete(auth_client(student_user), lessons[0])
    EnrollmentFactory(course=course, status="dropped")
    res = auth_client(faculty_user).get(f"{API}/courses/{course.pk}/progress/")
    assert res.status_code == 200
    rows = {r["student_detail"]["email"]: r for r in res.data["results"]}
    row = rows[student_user.email]
    assert (row["progress_percent"], row["completed_lessons"], row["total_lessons"]) == (25, 1, 4)
    assert len(rows) == 1
    assert auth_client(student_user).get(f"{API}/courses/{course.pk}/progress/").status_code == 403


def test_adding_and_removing_lessons_recomputes(auth_client, faculty_user, student_user, setup):
    course, chapter, lessons, enrollment = setup
    client = auth_client(student_user)
    for lesson in lessons[:2]:
        complete(client, lesson)
    manager = auth_client(faculty_user)

    for lesson in lessons[2:]:
        assert manager.delete(f"{API}/lessons/{lesson.pk}/").status_code == 204
    enrollment.refresh_from_db()
    assert (enrollment.progress_percent, enrollment.status) == (100, "completed")

    manager.post(f"{API}/chapters/{chapter.pk}/lessons/", {"title": "New"}, format="json")
    enrollment.refresh_from_db()
    assert (enrollment.progress_percent, enrollment.status) == (67, "completed")


def test_tree_marks_completed_lessons(auth_client, student_user, setup):
    course, _, lessons, _ = setup
    client = auth_client(student_user)
    complete(client, lessons[1])
    tree = client.get(f"{API}/courses/{course.pk}/tree/").data
    flags = [lesson["completed"] for lesson in tree["modules"][0]["chapters"][0]["lessons"]]
    assert flags == [False, True, False, False]
    assert tree["progress_percent"] == 25
