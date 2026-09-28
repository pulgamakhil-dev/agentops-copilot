from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.guardrails import ActionRisk


class ApprovalStatus(str, Enum):
    """
    Lifecycle state for a human approval request.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class ApprovalRequest(BaseModel):
    """
    Represents an action that requires human review before execution.
    """
    
    approval_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    action_name: str
    action_risk: ActionRisk

    resource_type: str | None = None
    resource_name: str | None = None
            
    reason: str
    requested_by: str = "agentops_copilot"


    status: ApprovalStatus = ApprovalStatus.PENDING

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Human-review audit information.
    reviewer: str | None = None
    comment: str | None = None
    decided_at: datetime | None = None

    


class ApprovalDecision(BaseModel):
    """
    Human decision applied to an approval request.
    """

    approval_id: str
    approved: bool
    reviewer: str
    comment: str | None = None