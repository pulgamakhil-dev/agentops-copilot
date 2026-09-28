from app.core.permissions import ROLE_PERMISSIONS, Permission, has_permission
from app.core.security import UserRole


def test_viewer_permissions() -> None:
    """Viewer can read operational information but cannot modify it."""

    roles = [UserRole.VIEWER]
    assert Permission.VIEW_AUDIT_HISTORY not in ROLE_PERMISSIONS[UserRole.VIEWER]
    assert has_permission(
        roles,
        Permission.VIEW_MONITORING,
    )

    assert has_permission(
        roles,
        Permission.VIEW_EXECUTION_HISTORY,
    )

    assert not has_permission(
        roles,
        Permission.REQUEST_ACTION,
    )

    assert not has_permission(
        roles,
        Permission.APPROVE_ACTION,
    )

    assert not has_permission(
        roles,
        Permission.EXECUTE_ACTION,
    )


def test_operator_permissions() -> None:
    """Operator can request and execute, but cannot approve."""

    roles = [UserRole.OPERATOR]
    assert Permission.VIEW_AUDIT_HISTORY not in ROLE_PERMISSIONS[UserRole.OPERATOR]
    assert has_permission(
        roles,
        Permission.REQUEST_ACTION,
    )

    assert has_permission(
        roles,
        Permission.EXECUTE_ACTION,
    )

    assert not has_permission(
        roles,
        Permission.APPROVE_ACTION,
    )


def test_approver_permissions() -> None:
    """Approver can approve actions but cannot execute them."""

    roles = [UserRole.APPROVER]
    assert Permission.VIEW_AUDIT_HISTORY in ROLE_PERMISSIONS[UserRole.APPROVER]
    assert has_permission(
        roles,
        Permission.APPROVE_ACTION,
    )

    assert not has_permission(
        roles,
        Permission.EXECUTE_ACTION,
    )


def test_admin_has_all_permissions() -> None:
    """Admin currently receives every defined permission."""

    roles = [UserRole.ADMIN]

    for permission in Permission:
        assert has_permission(
            roles,
            permission,
        )


def test_multiple_roles_combine_permissions() -> None:
    """Permissions from multiple assigned roles are combined."""

    roles = [
        UserRole.VIEWER,
        UserRole.APPROVER,
    ]

    assert has_permission(
        roles,
        Permission.VIEW_MONITORING,
    )

    assert has_permission(
        roles,
        Permission.APPROVE_ACTION,
    )

    assert not has_permission(
        roles,
        Permission.EXECUTE_ACTION,
    )


def test_no_roles_have_no_permissions() -> None:
    """An identity without roles receives no permissions."""

    assert not has_permission(
        [],
        Permission.VIEW_MONITORING,
    )