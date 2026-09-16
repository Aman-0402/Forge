import pytest
from django.core.management import call_command

from apps.accounts.models import Department
from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.courses.models import Enrollment
from apps.courses.tests.factories import CourseFactory, EnrollmentFactory
from apps.notifications.models import Notification

API = "/api/v1"

pytestmark = pytest.mark.django_db


def statuses(course):
    return dict(Enrollment.objects.filter(course=course).values_list("student_id", "status"))


@pytest.fixture
def cse():
    return Department.objects.create(name="Computer Science", code="CSE")


# ---------- self enrollment ----------


def test_student_self_enrolls_in_open_course(auth_client, student_user):
    course = CourseFactory(enrollment_mode="open")
    res = auth_client(student_user).post(f"{API}/courses/{course.pk}/enroll/")
    assert res.status_code == 201, res.data
    assert res.data["status"] == "active" and res.data["source"] == "self"
    again = auth_client(student_user).post(f"{API}/courses/{course.pk}/enroll/")
    assert again.status_code == 200
    assert Enrollment.objects.count() == 1
    assert AuditLog.objects.filter(action="enrollment.self").exists()


def test_self_enroll_rejected_for_manual_course(auth_client, student_user):
    course = CourseFactory(enrollment_mode="manual")
    assert auth_client(student_user).post(f"{API}/courses/{course.pk}/enroll/").status_code == 403


def test_self_enroll_rejected_for_draft_and_non_students(auth_client, faculty_user, student_user):
    draft = CourseFactory(enrollment_mode="open", status="draft")
    assert auth_client(student_user).post(f"{API}/courses/{draft.pk}/enroll/").status_code == 404
    live = CourseFactory(enrollment_mode="open")
    assert auth_client(faculty_user).post(f"{API}/courses/{live.pk}/enroll/").status_code == 403


def test_student_drops_and_rejoins_open_course(auth_client, student_user):
    course = CourseFactory(enrollment_mode="open")
    client = auth_client(student_user)
    client.post(f"{API}/courses/{course.pk}/enroll/")
    assert client.post(f"{API}/courses/{course.pk}/drop/").status_code == 200
    assert statuses(course) == {student_user.pk: "dropped"}
    assert client.post(f"{API}/courses/{course.pk}/enroll/").status_code == 200
    assert statuses(course) == {student_user.pk: "active"}


def test_student_cannot_drop_manual_course(auth_client, student_user):
    course = CourseFactory(enrollment_mode="manual")
    EnrollmentFactory(course=course, student=student_user)
    assert auth_client(student_user).post(f"{API}/courses/{course.pk}/drop/").status_code == 403


# ---------- manager enrollment ----------


def test_manager_bulk_adds_by_ids_batch_and_department(auth_client, faculty_user, cse):
    course = CourseFactory(instructor=faculty_user, enrollment_mode="manual")
    by_id = UserFactory(role="student")
    by_batch = UserFactory(role="student")
    by_batch.student_profile.batch = "2026"
    by_batch.student_profile.save()
    by_dept = UserFactory(role="student", department=cse)
    already = UserFactory(role="student")
    EnrollmentFactory(course=course, student=already)
    not_student = UserFactory(role="faculty")
    inactive = UserFactory(role="student", is_active=False)

    res = auth_client(faculty_user).post(
        f"{API}/courses/{course.pk}/enrollments/",
        {
            "student_ids": [by_id.pk, already.pk, not_student.pk, inactive.pk, 999999],
            "batch": "2026",
            "department": cse.pk,
        },
        format="json",
    )
    assert res.status_code == 200, res.data
    assert set(res.data["enrolled"]) == {by_id.pk, by_batch.pk, by_dept.pk}
    assert res.data["already_enrolled"] == [already.pk]
    assert set(res.data["invalid"]) == {not_student.pk, inactive.pk, 999999}
    assert Notification.objects.filter(kind="enrollment", recipient=by_id).exists()
    assert AuditLog.objects.filter(action="enrollment.bulk_add").exists()


def test_bulk_add_requires_published_course(auth_client, faculty_user, student_user):
    course = CourseFactory(instructor=faculty_user, status="draft")
    res = auth_client(faculty_user).post(
        f"{API}/courses/{course.pk}/enrollments/", {"student_ids": [student_user.pk]}, format="json"
    )
    assert res.status_code == 400


def test_non_manager_cannot_list_or_add(auth_client, student_user):
    course = CourseFactory()
    other_faculty = UserFactory(role="faculty")
    url = f"{API}/courses/{course.pk}/enrollments/"
    assert auth_client(other_faculty).get(url).status_code == 403
    assert auth_client(student_user).get(url).status_code == 403
    body = {"student_ids": [student_user.pk]}
    assert auth_client(other_faculty).post(url, body, format="json").status_code == 403


def test_manager_lists_enrollments_with_student_detail(auth_client, faculty_user):
    course = CourseFactory(instructor=faculty_user)
    s = UserFactory(role="student", email="list-me@forge.test")
    EnrollmentFactory(course=course, student=s, progress_percent=40)
    EnrollmentFactory(course=course, status="dropped")
    client = auth_client(faculty_user)
    rows = client.get(f"{API}/courses/{course.pk}/enrollments/").data["results"]
    assert len(rows) == 2
    active = client.get(f"{API}/courses/{course.pk}/enrollments/", {"status": "active"})
    row = active.data["results"][0]
    assert row["student_detail"]["email"] == "list-me@forge.test"
    assert row["progress_percent"] == 40


def test_manager_removes_enrollment(auth_client, faculty_user):
    course = CourseFactory(instructor=faculty_user)
    enrollment = EnrollmentFactory(course=course)
    other = UserFactory(role="faculty")
    assert auth_client(other).delete(f"{API}/enrollments/{enrollment.pk}/").status_code == 403
    assert (
        auth_client(faculty_user).delete(f"{API}/enrollments/{enrollment.pk}/").status_code == 204
    )
    enrollment.refresh_from_db()
    assert enrollment.status == "dropped"


# ---------- my enrollments ----------


def test_my_enrollments(auth_client, student_user):
    a = CourseFactory(title="A")
    b = CourseFactory(title="B")
    EnrollmentFactory(course=a, student=student_user, progress_percent=50)
    EnrollmentFactory(course=b, student=student_user, status="dropped")
    EnrollmentFactory(course=a)
    client = auth_client(student_user)
    rows = client.get(f"{API}/me/enrollments/").data["results"]
    assert {r["course_detail"]["title"] for r in rows} == {"A", "B"}
    active = client.get(f"{API}/me/enrollments/", {"status": "active"}).data["results"]
    assert [(r["course_detail"]["title"], r["progress_percent"]) for r in active] == [("A", 50)]


def test_my_enrollments_students_only(auth_client, faculty_user):
    assert auth_client(faculty_user).get(f"{API}/me/enrollments/").status_code == 403


# ---------- automatic enrollment ----------


def test_publishing_auto_department_course_enrolls_department(auth_client, admin_user, cse):
    inside = UserFactory(role="student", department=cse)
    UserFactory(role="student")
    UserFactory(role="student", department=cse, is_active=False)
    course = CourseFactory(
        status="pending_approval", enrollment_mode="auto_department", department=cse
    )
    auth_client(admin_user).post(f"{API}/courses/{course.pk}/approve/")
    assert statuses(course) == {inside.pk: "active"}
    assert Enrollment.objects.get(course=course).source == "auto"


def test_new_student_joins_auto_courses(cse):
    course = CourseFactory(enrollment_mode="auto_department", department=cse)
    CourseFactory(enrollment_mode="auto_department", department=cse, status="draft")
    student = UserFactory(role="student", department=cse)
    assert statuses(course) == {student.pk: "active"}
    assert Enrollment.objects.filter(student=student).count() == 1


def test_batch_change_triggers_auto_batch(cse):
    course = CourseFactory(enrollment_mode="auto_batch", auto_enroll_batch="2027")
    student = UserFactory(role="student")
    assert statuses(course) == {}
    student.student_profile.batch = "2027"
    student.student_profile.save()
    assert statuses(course) == {student.pk: "active"}


def test_auto_sync_respects_dropped(cse):
    course = CourseFactory(enrollment_mode="auto_department", department=cse)
    student = UserFactory(role="student", department=cse)
    Enrollment.objects.filter(course=course, student=student).update(status="dropped")
    student.first_name = "Changed"
    student.save()
    call_command("sync_auto_enrollments")
    assert statuses(course) == {student.pk: "dropped"}


def test_switching_published_course_to_auto_syncs(auth_client, faculty_user, cse):
    student = UserFactory(role="student", department=cse)
    course = CourseFactory(instructor=faculty_user, enrollment_mode="manual")
    res = auth_client(faculty_user).patch(
        f"{API}/courses/{course.pk}/",
        {"enrollment_mode": "auto_department", "department": cse.pk},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert statuses(course) == {student.pk: "active"}


def test_sync_command_is_idempotent(cse):
    course = CourseFactory(enrollment_mode="auto_department", department=cse)
    UserFactory(role="student", department=cse)
    call_command("sync_auto_enrollments")
    call_command("sync_auto_enrollments")
    assert Enrollment.objects.filter(course=course).count() == 1
