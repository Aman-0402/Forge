"""Who may sit an exam.

Rule: if the exam lists allowed students, only they may sit it. Otherwise, if the exam
belongs to a course, students actively enrolled (or completed) in that course may.
Otherwise every active student may.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Exam

User = get_user_model()

ACTIVE_ENROLLMENT = ("active", "completed")
STUDENT_VISIBLE_STATUSES = (Exam.Status.SCHEDULED, Exam.Status.CLOSED)


def eligible_students(exam):
    students = User.objects.filter(role="student", is_active=True)
    allowed = exam.allowed_students.all()
    if allowed.exists():
        return students.filter(pk__in=allowed.values("pk"))
    if exam.course_id:
        return students.filter(
            enrollments__course_id=exam.course_id, enrollments__status__in=ACTIVE_ENROLLMENT
        ).distinct()
    return students


def is_eligible(user, exam):
    if getattr(user, "role", None) != "student" or not user.is_active:
        return False
    return eligible_students(exam).filter(pk=user.pk).exists()


def student_exams(user):
    open_to_course_or_all = Q(allowed_students__isnull=True) & (
        Q(course__isnull=True)
        | Q(course__enrollments__student=user, course__enrollments__status__in=ACTIVE_ENROLLMENT)
    )
    return (
        Exam.objects.filter(status__in=STUDENT_VISIBLE_STATUSES)
        .filter(Q(allowed_students=user) | open_to_course_or_all)
        .distinct()
    )
