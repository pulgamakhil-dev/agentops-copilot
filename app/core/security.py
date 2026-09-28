from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    """
    Roles supported by AgentOps Copilot.

    Permissions will be mapped to these roles separately
    so authorization rules are not hardcoded inside API routes.
    """

    VIEWER = "viewer"
    OPERATOR = "operator"
    APPROVER = "approver"
    ADMIN = "admin"


class UserIdentity(BaseModel):
    """
    Represents an authenticated user inside the application.

    Authentication providers can later populate this model
    from JWT, OIDC, OAuth, or enterprise identity systems.
    """

    user_id: str
    username: str
    roles: list[UserRole]