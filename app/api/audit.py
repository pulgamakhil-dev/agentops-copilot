from fastapi import APIRouter, Depends, Query

from app.core.authorization import require_permission
from app.core.permissions import Permission
from app.core.security import UserIdentity
from app.models.audit import AuditHistoryResponse
from app.services.audit_history_service import audit_history_service


router = APIRouter(
    prefix="/audit",
    tags=["audit"],
)


@router.get(
    "/history",
    response_model=AuditHistoryResponse,
)
def get_audit_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    approval_id: str | None = Query(default=None),
    execution_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_name: str | None = Query(default=None),
    current_user: UserIdentity = Depends(
        require_permission(Permission.VIEW_AUDIT_HISTORY)
    ),
) -> AuditHistoryResponse:
    """
    Return paginated audit events with optional filters.

    Access requires the dedicated VIEW_AUDIT_HISTORY permission.
    """

    return audit_history_service.list_events(
        limit=limit,
        offset=offset,
        event_type=event_type,
        actor=actor,
        approval_id=approval_id,
        execution_id=execution_id,
        resource_type=resource_type,
        resource_name=resource_name,
    )