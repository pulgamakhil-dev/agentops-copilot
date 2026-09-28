import pytest
from fastapi import HTTPException

from app.core.auth import get_current_user
from app.core.security import UserRole


def test_valid_user_authentication() -> None:
    """Valid headers should create an authenticated identity."""

    user = get_current_user(
        x_user_id="user-001",
        x_username="test-operator",
        x_user_roles="operator",
    )

    assert user.user_id == "user-001"
    assert user.username == "test-operator"
    assert user.roles == [UserRole.OPERATOR]


def test_multiple_roles() -> None:
    """A user may have multiple valid roles."""

    user = get_current_user(
        x_user_id="user-002",
        x_username="test-user",
        x_user_roles="viewer,approver",
    )

    assert UserRole.VIEWER in user.roles
    assert UserRole.APPROVER in user.roles
    assert len(user.roles) == 2


def test_missing_user_id() -> None:
    """Missing identity information must be rejected."""

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            x_user_id=None,
            x_username="test-user",
            x_user_roles="viewer",
        )

    assert exc.value.status_code == 401


def test_missing_username() -> None:
    """Missing username must be rejected."""

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            x_user_id="user-003",
            x_username=None,
            x_user_roles="viewer",
        )

    assert exc.value.status_code == 401


def test_missing_roles() -> None:
    """A user without supplied roles must be rejected."""

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            x_user_id="user-004",
            x_username="test-user",
            x_user_roles=None,
        )

    assert exc.value.status_code == 401


def test_invalid_role() -> None:
    """Unknown roles must not be accepted."""

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            x_user_id="user-005",
            x_username="test-user",
            x_user_roles="superuser",
        )

    assert exc.value.status_code == 401


def test_empty_role_header() -> None:
    """An empty role list must be rejected."""

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            x_user_id="user-006",
            x_username="test-user",
            x_user_roles=" , ",
        )

    assert exc.value.status_code == 401