import pytest
from fastapi import HTTPException

from app.core.authorization import require_permission
from app.core.permissions import Permission
from app.core.security import UserIdentity, UserRole


def test_operator_can_execute_action() -> None:
    """Operator should be allowed to execute approved actions."""

    user = UserIdentity(
        user_id="user-001",
        username="test-operator",
        roles=[UserRole.OPERATOR],
    )

    dependency = require_permission(
        Permission.EXECUTE_ACTION
    )

    result = dependency(current_user=user)

    assert result == user


def test_viewer_cannot_execute_action() -> None:
    """Viewer must not be allowed to execute actions."""

    user = UserIdentity(
        user_id="user-002",
        username="test-viewer",
        roles=[UserRole.VIEWER],
    )

    dependency = require_permission(
        Permission.EXECUTE_ACTION
    )

    with pytest.raises(HTTPException) as exc:
        dependency(current_user=user)

    assert exc.value.status_code == 403
    assert "execute_action" in exc.value.detail


def test_approver_can_approve_action() -> None:
    """Approver should have approval permission."""

    user = UserIdentity(
        user_id="user-003",
        username="test-approver",
        roles=[UserRole.APPROVER],
    )

    dependency = require_permission(
        Permission.APPROVE_ACTION
    )

    result = dependency(current_user=user)

    assert result == user


def test_operator_cannot_approve_action() -> None:
    """Operator and approver responsibilities remain separated."""

    user = UserIdentity(
        user_id="user-004",
        username="test-operator",
        roles=[UserRole.OPERATOR],
    )

    dependency = require_permission(
        Permission.APPROVE_ACTION
    )

    with pytest.raises(HTTPException) as exc:
        dependency(current_user=user)

    assert exc.value.status_code == 403


def test_viewer_can_view_execution_history() -> None:
    """Viewer should have read-only execution history access."""

    user = UserIdentity(
        user_id="user-005",
        username="test-viewer",
        roles=[UserRole.VIEWER],
    )

    dependency = require_permission(
        Permission.VIEW_EXECUTION_HISTORY
    )

    result = dependency(current_user=user)

    assert result == user


def test_admin_has_execution_permission() -> None:
    """Admin should inherit all currently defined permissions."""

    user = UserIdentity(
        user_id="user-006",
        username="test-admin",
        roles=[UserRole.ADMIN],
    )

    dependency = require_permission(
        Permission.EXECUTE_ACTION
    )

    result = dependency(current_user=user)

    assert result == user