"""Enrollment services: self, manual bulk, automatic rules."""

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import log_action
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Course, Enrollment

User = get_user_model()

AUTO_MODES = (Course.EnrollmentMode.AUTO_DEPARTMENT, Course.EnrollmentMode.AUTO_BATCH)


def _notify_enrolled(course, students):
    if students:
        notify(
            students,
            f"Enrolled: {course.title}",
            f"You are now enrolled in '{course.title}'.",
            kind=Notification.Kind.ENROLLMENT,
            link=f"/courses/{course.pk}",
        )


def enroll(course, student, *, source, actor=None):
    """Create or reactivate an enrollment.

    Returns ``(enrollment, change)`` where change is "created", "reactivated" or None.
    Automatic sync never reactivates a dropped enrollment.
    """
    enrollment, created = Enrollment.objects.get_or_create(
        course=course,
        student=student,
        defaults={"source": source, "enrolled_by": actor},
    )
    if created:
        return enrollment, "created"
    if enrollment.status == Enrollment.Status.DROPPED and source != Enrollment.Source.AUTO:
        enrollment.status = Enrollment.Status.ACTIVE
        enrollment.source = source
        enrollment.enrolled_by = actor
        enrollment.save(update_fields=["status", "source", "enrolled_by", "updated_at"])
        return enrollment, "reactivated"
    return enrollment, None


def _require_student(user):
    if user.role != "student":
        raise PermissionDenied("Only students can enroll.")


def _require_open(course):
    if course.status != Course.Status.PUBLISHED:
        raise ValidationError({"detail": ["This course is not open for enrollment."]})
    if course.enrollment_mode != Course.EnrollmentMode.OPEN:
        raise PermissionDenied("Enrollment for this course is managed by the instructor.")


@transaction.atomic
def self_enroll(*, actor, course, request=None):
    _require_student(actor)
    _require_open(course)
    enrollment, changed = enroll(course, actor, source=Enrollment.Source.SELF, actor=actor)
    if changed:
        log_action(actor, "enrollment.self", target=enrollment, request=request)
    return enrollment, changed


@transaction.atomic
def self_drop(*, actor, course, request=None):
    _require_student(actor)
    if course.enrollment_mode != Course.EnrollmentMode.OPEN:
        raise PermissionDenied("Ask your instructor to remove you from this course.")
    enrollment = Enrollment.objects.filter(course=course, student=actor).first()
    if not enrollment:
        raise ValidationError({"detail": ["You are not enrolled in this course."]})
    return drop(actor=actor, enrollment=enrollment, request=request)


@transaction.atomic
def drop(*, actor, enrollment, request=None):
    if enrollment.status != Enrollment.Status.DROPPED:
        enrollment.status = Enrollment.Status.DROPPED
        enrollment.save(update_fields=["status", "updated_at"])
        log_action(actor, "enrollment.drop", target=enrollment, request=request)
    return enrollment


@transaction.atomic
def bulk_enroll(*, actor, course, student_ids=(), batch="", department=None, request=None):
    if course.status != Course.Status.PUBLISHED:
        raise ValidationError({"detail": ["Publish the course before enrolling students."]})

    requested = list(dict.fromkeys(student_ids))
    valid = {u.pk: u for u in User.objects.filter(pk__in=requested, role="student", is_active=True)}
    invalid = [pk for pk in requested if pk not in valid]

    candidates = dict(valid)
    students = User.objects.filter(role="student", is_active=True)
    if batch:
        candidates.update({u.pk: u for u in students.filter(student_profile__batch=batch)})
    if department:
        candidates.update({u.pk: u for u in students.filter(department=department)})

    enrolled, already, newly = [], [], []
    for student in candidates.values():
        _, changed = enroll(course, student, source=Enrollment.Source.MANUAL, actor=actor)
        if changed:
            enrolled.append(student.pk)
            newly.append(student)
        else:
            already.append(student.pk)

    _notify_enrolled(course, newly)
    log_action(
        actor,
        "enrollment.bulk_add",
        target=course,
        metadata={"enrolled": len(enrolled), "already": len(already), "invalid": len(invalid)},
        request=request,
    )
    return {"enrolled": enrolled, "already_enrolled": already, "invalid": invalid}


# ---------- automatic rules ----------


def auto_rule_students(course):
    students = User.objects.filter(role="student", is_active=True)
    if course.enrollment_mode == Course.EnrollmentMode.AUTO_DEPARTMENT and course.department_id:
        return students.filter(department_id=course.department_id)
    if course.enrollment_mode == Course.EnrollmentMode.AUTO_BATCH and course.auto_enroll_batch:
        return students.filter(student_profile__batch=course.auto_enroll_batch)
    return students.none()


def sync_auto_enrollments(course, actor=None):
    """Enroll every student matching the course's automatic rule. Returns new enrollments."""
    if course.status != Course.Status.PUBLISHED or course.enrollment_mode not in AUTO_MODES:
        return []
    newly = []
    for student in auto_rule_students(course):
        enrollment, changed = enroll(course, student, source=Enrollment.Source.AUTO, actor=actor)
        if changed:
            newly.append(enrollment)
    _notify_enrolled(course, [e.student for e in newly])
    return newly


def sync_student_auto_enrollments(student):
    if student.role != "student" or not student.is_active:
        return []
    courses = Course.objects.filter(status=Course.Status.PUBLISHED)
    matches = []
    if student.department_id:
        matches += list(
            courses.filter(
                enrollment_mode=Course.EnrollmentMode.AUTO_DEPARTMENT,
                department_id=student.department_id,
            )
        )
    profile = getattr(student, "student_profile", None)
    if profile and profile.batch:
        matches += list(
            courses.filter(
                enrollment_mode=Course.EnrollmentMode.AUTO_BATCH,
                auto_enroll_batch=profile.batch,
            )
        )
    newly = []
    for course in matches:
        enrollment, changed = enroll(course, student, source=Enrollment.Source.AUTO)
        if changed:
            newly.append(enrollment)
            _notify_enrolled(course, [student])
    return newly
