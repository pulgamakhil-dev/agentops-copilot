from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    """
    API representation of a persisted audit event.
    """

    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_type: str
    actor: str

    action_name: str | None = None
    resource_type: str | None = None
    resource_name: str | None = None

    approval_id: str | None = None
    execution_id: str | None = None

    outcome: str | None = None
    message: str | None = None

    created_at: datetime


class AuditHistoryResponse(BaseModel):
    """
    Paginated response returned by the audit-history API.
    """

    items: list[AuditEventResponse]
    total: int
    limit: int
    offset: int