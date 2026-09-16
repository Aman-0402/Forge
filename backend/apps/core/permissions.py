from rest_framework.permissions import BasePermission

ADMIN = "admin"
FACULTY = "faculty"
STUDENT = "student"


def _has_role(request, *roles):
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and getattr(user, "role", None) in roles)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return _has_role(request, ADMIN)


class IsFaculty(BasePermission):
    def has_permission(self, request, view):
        return _has_role(request, FACULTY)


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return _has_role(request, STUDENT)


class IsAdminOrFaculty(BasePermission):
    def has_permission(self, request, view):
        return _has_role(request, ADMIN, FACULTY)


class IsOwnerOrAdmin(BasePermission):
    """Object-level: allow admins, or the user referenced by ``obj.user_id``.

    Views may set ``owner_field`` (default ``"user_id"``) to point elsewhere.
    """

    def has_object_permission(self, request, view, obj):
        if _has_role(request, ADMIN):
            return True
        field = getattr(view, "owner_field", "user_id")
        return getattr(obj, field, None) == request.user.pk
