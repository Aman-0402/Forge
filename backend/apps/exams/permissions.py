"""Access rules for question banks and exams."""

from django.db.models import Q
from rest_framework.permissions import BasePermission

from .models import Exam, QuestionBank


def is_staff_role(user):
    return bool(user and user.is_authenticated and user.role in ("admin", "faculty"))


class IsAdminOrFacultyRole(BasePermission):
    message = "Only faculty and administrators can manage exams."

    def has_permission(self, request, view):
        return is_staff_role(request.user)


# ---------- banks ----------


def readable_banks(user):
    if user.role == "admin":
        return QuestionBank.objects.all()
    return QuestionBank.objects.filter(Q(owner=user) | Q(is_shared=True))


def can_edit_bank(user, bank):
    return user.role == "admin" or bank.owner_id == user.pk


# ---------- exams ----------


def can_manage_exam(user, exam):
    """Admin, the exam creator, or an instructor of the exam's course."""
    if not (user and user.is_authenticated):
        return False
    if user.role == "admin" or exam.created_by_id == user.pk:
        return True
    if exam.course_id:
        from apps.courses.permissions import can_manage_course

        return can_manage_course(user, exam.course)
    return False


def managed_exams(user):
    if user.role == "admin":
        return Exam.objects.all()
    return Exam.objects.filter(
        Q(created_by=user) | Q(course__instructor=user) | Q(course__co_instructors=user)
    ).distinct()
