import pytest

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.courses.models import Course
from apps.courses.tests.factories import CategoryFactory, CourseFactory, EnrollmentFactory
from apps.notifications.models import Notification

URL = "/api/v1/courses/"
CATEGORIES = "/api/v1/categories/"

pytestmark = pytest.mark.django_db


def detail(course, action=""):
    return f"{URL}{course.pk}/" + (f"{action}/" if action else "")


def titles(res):
    return {c["title"] for c in res.data["results"]}


# ---------- categories ----------


def test_categories_read_all_write_admin(auth_client, admin_user, faculty_user, student_user):
    CategoryFactory(name="Programming")
    assert auth_client(student_user).get(CATEGORIES).data["results"][0]["slug"] == "programming"
    body = {"name": "Data Science", "kind": "subject"}
    assert auth_client(faculty_user).post(CATEGORIES, body, format="json").status_code == 403
    res = auth_client(admin_user).post(CATEGORIES, body, format="json")
    assert res.status_code == 201 and res.data["slug"] == "data-science"


# ---------- create ----------


def test_faculty_creates_draft_course_as_instructor(auth_client, faculty_user):
    cat = CategoryFactory()
    res = auth_client(faculty_user).post(
        URL,
        {
            "title": "Intro to Python",
            "description": "Basics",
            "categories": [cat.pk],
            "level": "beginner",
        },
        format="json",
    )
    assert res.status_code == 201, res.data
    course = Course.objects.get(pk=res.data["id"])
    assert course.instructor == faculty_user
    assert course.status == Course.Status.DRAFT
    assert course.slug == "intro-to-python"
    assert res.data["instructor_detail"]["email"] == faculty_user.email
    assert AuditLog.objects.filter(action="course.create", target_id=str(course.pk)).exists()


def test_faculty_cannot_assign_other_instructor(auth_client, faculty_user):
    other = UserFactory(role="faculty")
    res = auth_client(faculty_user).post(URL, {"title": "X", "instructor": other.pk}, format="json")
    assert res.status_code == 201
    assert Course.objects.get(pk=res.data["id"]).instructor == faculty_user


def test_admin_must_pick_faculty_instructor(auth_client, admin_user, student_user):
    fac = UserFactory(role="faculty")
    client = auth_client(admin_user)
    assert client.post(URL, {"title": "No instructor"}, format="json").status_code == 400
    bad = client.post(URL, {"title": "Student", "instructor": student_user.pk}, format="json")
    assert bad.status_code == 400
    ok = client.post(URL, {"title": "Good", "instructor": fac.pk}, format="json")
    assert ok.status_code == 201


def test_student_cannot_create(auth_client, student_user):
    assert auth_client(student_user).post(URL, {"title": "x"}, format="json").status_code == 403


def test_duplicate_titles_get_unique_slugs(auth_client, faculty_user):
    client = auth_client(faculty_user)
    a = client.post(URL, {"title": "Same"}, format="json").data["slug"]
    b = client.post(URL, {"title": "Same"}, format="json").data["slug"]
    assert a == "same" and b != a and b.startswith("same-")


def test_co_instructors_must_be_faculty(auth_client, faculty_user, student_user):
    res = auth_client(faculty_user).post(
        URL, {"title": "Team", "co_instructors": [student_user.pk]}, format="json"
    )
    assert res.status_code == 400


# ---------- visibility ----------


def test_list_visibility_by_role(auth_client, admin_user, faculty_user, student_user):
    CourseFactory(title="published")
    CourseFactory(title="other draft", status="draft")
    CourseFactory(title="my draft", status="draft", instructor=faculty_user)
    co = CourseFactory(title="co draft", status="draft")
    co.co_instructors.add(faculty_user)
    CourseFactory(title="archived", status="archived")

    assert titles(auth_client(student_user).get(URL)) == {"published"}
    assert titles(auth_client(faculty_user).get(URL)) == {"published", "my draft", "co draft"}
    assert len(titles(auth_client(admin_user).get(URL))) == 5


def test_student_sees_enrollment_state(auth_client, student_user):
    enrolled = CourseFactory(title="enrolled")
    CourseFactory(title="not enrolled")
    EnrollmentFactory(course=enrolled, student=student_user)
    rows = {c["title"]: c for c in auth_client(student_user).get(URL).data["results"]}
    assert rows["enrolled"]["is_enrolled"] is True
    assert rows["not enrolled"]["is_enrolled"] is False


def test_filters_and_search(auth_client, student_user):
    cat = CategoryFactory()
    py = CourseFactory(title="Python Basics", level="beginner")
    py.categories.add(cat)
    CourseFactory(title="Advanced Java", level="advanced")
    client = auth_client(student_user)
    assert titles(client.get(URL, {"search": "python"})) == {"Python Basics"}
    assert titles(client.get(URL, {"level": "advanced"})) == {"Advanced Java"}
    assert titles(client.get(URL, {"categories": cat.pk})) == {"Python Basics"}


def test_student_cannot_open_draft_detail(auth_client, student_user):
    draft = CourseFactory(status="draft")
    assert auth_client(student_user).get(detail(draft)).status_code == 404


# ---------- update / delete ----------


def test_only_managers_can_edit(auth_client, faculty_user):
    course = CourseFactory(instructor=faculty_user)
    other = UserFactory(role="faculty")
    body = {"title": "Renamed"}
    assert auth_client(other).patch(detail(course), body, format="json").status_code == 403
    assert auth_client(faculty_user).patch(detail(course), body, format="json").status_code == 200
    course.co_instructors.add(other)
    assert auth_client(other).patch(detail(course), body, format="json").status_code == 200


def test_status_cannot_be_patched_directly(auth_client, faculty_user):
    course = CourseFactory(instructor=faculty_user, status="draft")
    auth_client(faculty_user).patch(detail(course), {"status": "published"}, format="json")
    course.refresh_from_db()
    assert course.status == "draft"


def test_delete_only_empty_drafts(auth_client, faculty_user):
    draft = CourseFactory(instructor=faculty_user, status="draft")
    live = CourseFactory(instructor=faculty_user)
    EnrollmentFactory(course=live)
    client = auth_client(faculty_user)
    assert client.delete(detail(live)).status_code == 400
    assert client.delete(detail(draft)).status_code == 204


# ---------- approval flow ----------


def test_submit_approve_flow_with_notifications(auth_client, admin_user, faculty_user):
    course = CourseFactory(instructor=faculty_user, status="draft")
    res = auth_client(faculty_user).post(detail(course, "submit-for-approval"))
    assert res.status_code == 200 and res.data["status"] == "pending_approval"
    assert Notification.objects.filter(recipient=admin_user, kind="info").exists()

    res = auth_client(admin_user).post(detail(course, "approve"))
    assert res.status_code == 200 and res.data["status"] == "published"
    course.refresh_from_db()
    assert course.approved_by == admin_user and course.approved_at
    assert Notification.objects.filter(recipient=faculty_user).exists()
    actions = set(AuditLog.objects.values_list("action", flat=True))
    assert {"course.submit", "course.approve"} <= actions


def test_reject_returns_to_draft_with_reason(auth_client, admin_user, faculty_user):
    course = CourseFactory(instructor=faculty_user, status="pending_approval")
    res = auth_client(admin_user).post(
        detail(course, "reject"), {"reason": "Add syllabus"}, format="json"
    )
    assert res.status_code == 200
    course.refresh_from_db()
    assert course.status == "draft" and course.rejection_reason == "Add syllabus"


def test_reject_requires_reason(auth_client, admin_user):
    course = CourseFactory(status="pending_approval")
    assert (
        auth_client(admin_user).post(detail(course, "reject"), {}, format="json").status_code == 400
    )


def test_faculty_cannot_approve(auth_client, faculty_user):
    course = CourseFactory(instructor=faculty_user, status="pending_approval")
    assert auth_client(faculty_user).post(detail(course, "approve")).status_code == 403


def test_invalid_transitions(auth_client, admin_user, faculty_user):
    published = CourseFactory(instructor=faculty_user)
    archived = CourseFactory(instructor=faculty_user, status="archived")
    assert (
        auth_client(faculty_user).post(detail(published, "submit-for-approval")).status_code == 400
    )
    assert auth_client(admin_user).post(detail(archived, "approve")).status_code == 400


def test_admin_can_publish_draft_directly_and_archive(auth_client, admin_user):
    course = CourseFactory(status="draft")
    client = auth_client(admin_user)
    assert client.post(detail(course, "approve")).data["status"] == "published"
    assert client.post(detail(course, "archive")).data["status"] == "archived"


def test_faculty_can_archive_own(auth_client, faculty_user):
    course = CourseFactory(instructor=faculty_user)
    assert auth_client(faculty_user).post(detail(course, "archive")).data["status"] == "archived"
