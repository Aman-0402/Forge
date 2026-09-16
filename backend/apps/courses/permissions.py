"""Course access rules shared by every courses endpoint."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Course, Enrollment

ACTIVE_ENROLLMENT = (Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED)


def is_admin(user):
    return getattr(user, "role", None) == "admin"


def can_manage_course(user, course):
    """Admin, the instructor, or a co-instructor."""
    if not (user and user.is_authenticated):
        return False
    if is_admin(user) or course.instructor_id == user.pk:
        return True
    return course.co_instructors.filter(pk=user.pk).exists()


def get_enrollment(user, course):
    if not (user and user.is_authenticated) or user.role != "student":
        return None
    return Enrollment.objects.filter(
        course=course, student=user, status__in=ACTIVE_ENROLLMENT
    ).first()


def can_view_course(user, course):
    if can_manage_course(user, course):
        return True
    if course.status == Course.Status.PUBLISHED:
        return True
    return course.status == Course.Status.ARCHIVED and get_enrollment(user, course) is not None


def can_access_content(user, course):
    """Full lesson content: managers and enrolled students."""
    return can_manage_course(user, course) or get_enrollment(user, course) is not None


class CanCreateCourse(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in ("admin", "faculty")


class IsCourseManagerOrReadOnly(BasePermission):
    """Object-level for Course: reads pass (queryset already filters), writes need a manager."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return can_manage_course(request.user, obj)
