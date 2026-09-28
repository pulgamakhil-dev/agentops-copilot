from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.core.permissions import Permission, has_permission
from app.core.security import UserIdentity


def require_permission(
    permission: Permission,
) -> Callable[..., UserIdentity]:
    """
    Create a FastAPI dependency that requires a specific permission.

    Authentication and authorization remain separate:
    - get_current_user() resolves the authenticated identity.
    - require_permission() verifies that identity is authorized.
    """

    def permission_dependency(
        current_user: UserIdentity = Depends(get_current_user),
    ) -> UserIdentity:
        """
        Validate that the authenticated user has the
        permission required by the API endpoint.
        """

        if not has_permission(
            current_user.roles,
            permission,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission '{permission.value}' is required."
                ),
            )

        return current_user

    return permission_dependency