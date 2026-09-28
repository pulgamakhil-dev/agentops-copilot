from enum import Enum

from app.core.security import UserRole


class Permission(str, Enum):
    """
    Fine-grained permissions supported by AgentOps Copilot.
    """

    VIEW_MONITORING = "view_monitoring"
    VIEW_EXECUTION_HISTORY = "view_execution_history"
    VIEW_AUDIT_HISTORY = "view_audit_history"
    
    REQUEST_ACTION = "request_action"
    APPROVE_ACTION = "approve_action"
    EXECUTE_ACTION = "execute_action"


# Central role-to-permission mapping.
# API routes should not contain their own role-specific rules.
ROLE_PERMISSIONS = {
    UserRole.VIEWER: {
        Permission.VIEW_MONITORING,
        Permission.VIEW_EXECUTION_HISTORY,
    },

    UserRole.OPERATOR: {
        Permission.VIEW_MONITORING,
        Permission.VIEW_EXECUTION_HISTORY,
        Permission.REQUEST_ACTION,
        Permission.EXECUTE_ACTION,
    },

    UserRole.APPROVER: {
        Permission.VIEW_MONITORING,
        Permission.VIEW_EXECUTION_HISTORY,
        Permission.APPROVE_ACTION,
        Permission.VIEW_AUDIT_HISTORY,
    },

    UserRole.ADMIN: set(Permission),
}


def has_permission(
    roles: list[UserRole],
    permission: Permission,
) -> bool:
    """
    Return True when at least one assigned role grants
    the requested permission.
    """

    return any(
        permission in ROLE_PERMISSIONS.get(role, set())
        for role in roles
    )
