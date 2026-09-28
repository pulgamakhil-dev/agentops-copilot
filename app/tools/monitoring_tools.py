from typing import Any

from app.core.logging import get_logger
from app.db.database import SessionLocal
from app.services.monitoring_service import MonitoringService
from pydantic import BaseModel, Field
from langchain_core.tools import tool


logger = get_logger(__name__)


def _serialize_pipeline_run(run: Any) -> dict[str, Any]:
    """
    Convert a SQLAlchemy PipelineRun object into a clean dictionary.

    Returning plain dictionaries keeps the agent/tool boundary simple
    and avoids leaking ORM-specific objects into the LLM layer.
    """

    return {
        "run_id": run.run_id,
        "pipeline_name": run.pipeline_name,
        "business_domain": run.business_domain,
        "environment": run.environment,
        "source_system": run.source_system,
        "target_system": run.target_system,
        "orchestrator": run.orchestrator,
        "job_name": run.job_name,
        "status": run.status,
        "attempt": run.attempt,
        "scheduled_time": (
            run.scheduled_time.isoformat()
            if run.scheduled_time
            else None
        ),
        "start_time": (
            run.start_time.isoformat()
            if run.start_time
            else None
        ),
        "end_time": (
            run.end_time.isoformat()
            if run.end_time
            else None
        ),
        "duration_seconds": run.duration_seconds,
        "records_read": run.records_read,
        "records_written": run.records_written,
        "records_rejected": run.records_rejected,
        "data_quality_status": run.data_quality_status,
        "sla_seconds": run.sla_seconds,
        "sla_breach_seconds": run.sla_breach_seconds,
        "error_code": run.error_code,
        "error_category": run.error_category,
        "owner_team": run.owner_team,
        "region": run.region,
        "correlation_id": run.correlation_id,
        "incident_id": run.incident_id,
        "recovery_action": run.recovery_action,
    }

class FailedRunsInput(BaseModel):
    """
    Validated input for retrieving failed pipeline runs.
    """

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of failed runs to return.",
    )

    pipeline_name: str | None = Field(
        default=None,
        description="Optional pipeline name used to filter failed runs.",
    )


class PipelineHistoryInput(BaseModel):
    """
    Validated input for retrieving execution history.
    """

    pipeline_name: str = Field(
        ...,
        min_length=1,
        description="Name of the pipeline to inspect.",
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of pipeline runs to return.",
    )


class IncidentHistoryInput(BaseModel):
    """
    Validated input for retrieving incident history.
    """

    incident_id: str = Field(
        ...,
        min_length=1,
        description="Incident identifier to investigate.",
    )


class SLABreachesInput(BaseModel):
    """
    Validated input for retrieving SLA breaches.
    """

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of SLA breaches to return.",
    )


def get_failed_pipeline_runs(
    limit: int = 20,
    pipeline_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve recent failed pipeline runs.

    This tool is intentionally read-only. It does not allow the agent
    to modify pipeline state or execute remediation actions.
    """

    session = SessionLocal()

    try:
        service = MonitoringService(session)

        runs = service.get_failed_runs(
            limit=limit,
            pipeline_name=pipeline_name,
        )

        return [
            _serialize_pipeline_run(run)
            for run in runs
        ]

    except Exception:
        logger.exception(
            "Monitoring tool failed while retrieving failed runs."
        )
        raise

    finally:
        # Always close the session to prevent connection leaks.
        session.close()


def get_pipeline_history(
    pipeline_name: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Retrieve recent execution history for one pipeline.
    """

    session = SessionLocal()

    try:
        service = MonitoringService(session)

        runs = service.get_pipeline_history(
            pipeline_name=pipeline_name,
            limit=limit,
        )

        return [
            _serialize_pipeline_run(run)
            for run in runs
        ]

    except Exception:
        logger.exception(
            "Monitoring tool failed while retrieving pipeline history."
        )
        raise

    finally:
        session.close()


def get_incident_history(
    incident_id: str,
) -> list[dict[str, Any]]:
    """
    Retrieve all pipeline runs associated with an incident.

    This helps the agent compare an original failure with later retries.
    """

    session = SessionLocal()

    try:
        service = MonitoringService(session)

        runs = service.get_incident_runs(
            incident_id=incident_id,
        )

        return [
            _serialize_pipeline_run(run)
            for run in runs
        ]

    except Exception:
        logger.exception(
            "Monitoring tool failed while retrieving incident history."
        )
        raise

    finally:
        session.close()


def get_sla_breaches(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Retrieve pipeline runs that exceeded their configured SLA.
    """

    session = SessionLocal()

    try:
        service = MonitoringService(session)

        runs = service.get_sla_breaches(
            limit=limit,
        )

        return [
            _serialize_pipeline_run(run)
            for run in runs
        ]

    except Exception:
        logger.exception(
            "Monitoring tool failed while retrieving SLA breaches."
        )
        raise

    finally:
        session.close()


@tool(
    "get_failed_pipeline_runs",
    args_schema=FailedRunsInput,
)
def failed_pipeline_runs_tool(
    limit: int = 20,
    pipeline_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve recent failed pipeline executions.

    Use this tool when investigating pipeline failures or determining
    which pipelines are currently experiencing operational problems.
    """

    return get_failed_pipeline_runs(
        limit=limit,
        pipeline_name=pipeline_name,
    )


@tool(
    "get_pipeline_history",
    args_schema=PipelineHistoryInput,
)
def pipeline_history_tool(
    pipeline_name: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Retrieve execution history for a specific pipeline.

    Use this tool to compare successful runs, failed runs and retries.
    """

    return get_pipeline_history(
        pipeline_name=pipeline_name,
        limit=limit,
    )


@tool(
    "get_incident_history",
    args_schema=IncidentHistoryInput,
)
def incident_history_tool(
    incident_id: str,
) -> list[dict[str, Any]]:
    """
    Retrieve pipeline executions associated with an incident.

    Use this tool when investigating the lifecycle of a known incident.
    """

    return get_incident_history(
        incident_id=incident_id,
    )


@tool(
    "get_sla_breaches",
    args_schema=SLABreachesInput,
)
def sla_breaches_tool(
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Retrieve pipeline runs that exceeded their configured SLA.

    Use this tool when investigating performance or SLA violations.
    """

    return get_sla_breaches(
        limit=limit,
    )


# Explicit registry of tools available to the Monitoring Agent.
# Keeping this list controlled prevents arbitrary functions from
# becoming accessible to the LLM.
MONITORING_TOOLS = [
    failed_pipeline_runs_tool,
    pipeline_history_tool,
    incident_history_tool,
    sla_breaches_tool,
]