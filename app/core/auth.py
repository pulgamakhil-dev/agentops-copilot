from fastapi import Header, HTTPException, status

from app.core.security import UserIdentity, UserRole


def get_current_user(
    x_user_id: str | None = Header(
        default=None,
        alias="X-User-ID",
    ),
    x_username: str | None = Header(
        default=None,
        alias="X-Username",
    ),
    x_user_roles: str | None = Header(
        default=None,
        alias="X-User-Roles",
    ),
) -> UserIdentity:
    """
    Resolve the authenticated user for the current request.

    This local implementation uses request headers so the
    authentication flow can be tested without an external
    identity provider.

    In production, this dependency can be replaced by a
    JWT/OIDC-backed identity provider without changing
    downstream authorization logic.
    """

    if not x_user_id or not x_username or not x_user_roles:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
        )

    try:
        role_values = [
            role.strip().lower()
            for role in x_user_roles.split(",")
            if role.strip()
        ]

        roles = [
            UserRole(role)
            for role in role_values
        ]

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user role.",
        ) from exc

    if not roles:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="At least one valid user role is required.",
        )

    return UserIdentity(
        user_id=x_user_id,
        username=x_username,
        roles=roles,
    )