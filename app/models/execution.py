from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExecutionRecordResponse(BaseModel):
    """
    API response model for a persisted execution record.

    Keeps the API contract separate from the database model
    and exposes execution audit identity.
    """

    model_config = ConfigDict(from_attributes=True)

    execution_id: str
    approval_id: str
    action_name: str
    resource_type: str
    resource_name: str
    executor_provider: str

    # Authenticated actor who initiated the execution.
    # Older execution records may not contain this value.
    executed_by: str | None = None

    status: str
    message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ExecutionHistoryResponse(BaseModel):
    """
    Paginated API response for execution history.

    Provides execution records together with pagination
    metadata required by API clients and user interfaces.
    """

    items: list[ExecutionRecordResponse]
    total: int
    limit: int
    offset: int