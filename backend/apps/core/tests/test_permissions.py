from types import SimpleNamespace

import pytest

from apps.core.permissions import (
    IsAdmin,
    IsAdminOrFaculty,
    IsFaculty,
    IsOwnerOrAdmin,
    IsStudent,
)


def make_request(role=None, authenticated=True, pk=1):
    user = SimpleNamespace(role=role, is_authenticated=authenticated, pk=pk)
    return SimpleNamespace(user=user)


@pytest.mark.parametrize(
    ("perm", "role", "expected"),
    [
        (IsAdmin, "admin", True),
        (IsAdmin, "faculty", False),
        (IsAdmin, "student", False),
        (IsFaculty, "faculty", True),
        (IsFaculty, "admin", False),
        (IsStudent, "student", True),
        (IsStudent, "faculty", False),
        (IsAdminOrFaculty, "admin", True),
        (IsAdminOrFaculty, "faculty", True),
        (IsAdminOrFaculty, "student", False),
    ],
)
def test_role_permissions(perm, role, expected):
    assert perm().has_permission(make_request(role), None) is expected


@pytest.mark.parametrize("perm", [IsAdmin, IsFaculty, IsStudent, IsAdminOrFaculty])
def test_role_permissions_reject_anonymous(perm):
    assert perm().has_permission(make_request("admin", authenticated=False), None) is False


def test_owner_or_admin_allows_owner():
    obj = SimpleNamespace(user_id=7)
    assert IsOwnerOrAdmin().has_object_permission(make_request("student", pk=7), None, obj)


def test_owner_or_admin_allows_admin():
    obj = SimpleNamespace(user_id=7)
    assert IsOwnerOrAdmin().has_object_permission(make_request("admin", pk=1), None, obj)


def test_owner_or_admin_rejects_other_user():
    obj = SimpleNamespace(user_id=7)
    assert not IsOwnerOrAdmin().has_object_permission(make_request("student", pk=8), None, obj)
