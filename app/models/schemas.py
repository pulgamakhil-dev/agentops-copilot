from pydantic import BaseModel
from pydantic import BaseModel, Field
from typing import Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PipelineRunResponse(BaseModel):
    """
    API response model for pipeline execution information.

    from_attributes allows Pydantic to convert SQLAlchemy
    PipelineRun objects directly into API responses.
    """

    model_config = ConfigDict(from_attributes=True)

    run_id: str
    pipeline_name: str
    business_domain: str
    environment: str
    source_system: str
    target_system: str
    orchestrator: str
    job_name: str
    status: str
    attempt: int

    scheduled_time: datetime
    start_time: datetime
    end_time: Optional[datetime]

    duration_seconds: int
    records_read: int
    records_written: int
    records_rejected: int

    data_quality_status: str

    sla_seconds: int
    sla_breach_seconds: int

    error_code: Optional[str]
    error_category: Optional[str]

    owner_team: str
    region: str
    correlation_id: str

    incident_id: Optional[str]
    recovery_action: Optional[str]




class AgentQueryRequest(BaseModel):
    """
    Request payload for AgentOps Copilot queries.
    """

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Operational question for AgentOps Copilot.",
    )


class AgentQueryResponse(BaseModel):
    """
    Standard API response returned by AgentOps Copilot.

    Metadata is optional and can contain structured information
    such as approval IDs for controlled actions.
    """

    response: str
    metadata: dict[str, Any] | None = None