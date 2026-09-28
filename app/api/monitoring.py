from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.schemas import PipelineRunResponse
from app.services.monitoring_service import MonitoringService


router = APIRouter(
    prefix="/api/v1",
)

# Reusable database dependency.
# The session is automatically closed after the request completes.
DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.get(
    "/pipelines/failures",
    response_model=list[PipelineRunResponse],
    tags=["Pipeline Monitoring"],
)
def get_failed_pipeline_runs(
    db: DatabaseSession,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
):
    """
    Return recent failed pipeline executions.
    """

    service = MonitoringService(db)

    return service.get_failed_runs(
        limit=limit,
    )


@router.get(
    "/pipelines/sla-breaches",
    response_model=list[PipelineRunResponse],
    tags=["Pipeline Monitoring"],
)
def get_sla_breaches(
    db: DatabaseSession,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
):
    """
    Return pipeline executions that exceeded their SLA.
    """

    service = MonitoringService(db)

    return service.get_sla_breaches(
        limit=limit,
    )


@router.get(
    "/pipelines/{pipeline_name}/history",
    response_model=list[PipelineRunResponse],
    tags=["Pipeline Monitoring"],
)
def get_pipeline_history(
    pipeline_name: str,
    db: DatabaseSession,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
):
    """
    Return execution history for a specific pipeline.
    """

    service = MonitoringService(db)

    runs = service.get_pipeline_history(
        pipeline_name=pipeline_name,
        limit=limit,
    )

    if not runs:
        raise HTTPException(
            status_code=404,
            detail="Pipeline history not found.",
        )

    return runs


@router.get(
    "/incidents/{incident_id}",
    response_model=list[PipelineRunResponse],
    tags=["Incidents"],
)
def get_incident_history(
    incident_id: str,
    db: DatabaseSession,
):
    """
    Return all pipeline executions associated with an incident.
    """

    service = MonitoringService(db)

    runs = service.get_incident_runs(
        incident_id=incident_id,
    )

    if not runs:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    return runs