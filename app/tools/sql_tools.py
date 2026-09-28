from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.db.database import SessionLocal
from app.db.models import PipelineRun


logger = get_logger(__name__)


class PipelineStatsInput(BaseModel):
    """
    Input schema for pipeline-level operational statistics.
    """

    pipeline_name: str = Field(
        ...,
        min_length=1,
        description="Pipeline name to analyze.",
    )


class ErrorCategoryStatsInput(BaseModel):
    """
    Input schema for aggregated failure-category statistics.
    """

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of error categories to return.",
    )


class RecentRunsInput(BaseModel):
    """
    Input schema for recent pipeline execution lookup.
    """

    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of recent runs to return.",
    )


def get_pipeline_statistics(
    pipeline_name: str,
) -> dict[str, Any]:
    """
    Calculate operational statistics for a pipeline.

    This function performs approved read-only aggregation against
    pipeline execution data.
    """

    session = SessionLocal()

    try:
        total_runs = session.scalar(
            select(func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.pipeline_name == pipeline_name
            )
        )

        failed_runs = session.scalar(
            select(func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.pipeline_name == pipeline_name,
                PipelineRun.status == "FAILED",
            )
        )

        successful_runs = session.scalar(
            select(func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.pipeline_name == pipeline_name,
                PipelineRun.status == "SUCCESS",
            )
        )

        average_duration = session.scalar(
            select(
                func.avg(PipelineRun.duration_seconds)
            )
            .where(
                PipelineRun.pipeline_name == pipeline_name
            )
        )

        total_sla_breaches = session.scalar(
            select(func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.pipeline_name == pipeline_name,
                PipelineRun.sla_breach_seconds > 0,
            )
        )

        total_runs = total_runs or 0
        failed_runs = failed_runs or 0
        successful_runs = successful_runs or 0

        failure_rate = (
            round(
                (failed_runs / total_runs) * 100,
                2,
            )
            if total_runs
            else 0.0
        )

        return {
            "pipeline_name": pipeline_name,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "failure_rate_percent": failure_rate,
            "average_duration_seconds": (
                round(float(average_duration), 2)
                if average_duration is not None
                else None
            ),
            "sla_breach_runs": total_sla_breaches or 0,
        }

    except SQLAlchemyError:
        logger.exception(
            "Failed to calculate pipeline statistics."
        )
        raise

    finally:
        session.close()


def get_error_category_statistics(
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Aggregate failed runs by error category.
    """

    session = SessionLocal()

    try:
        query = (
            select(
                PipelineRun.error_category,
                func.count(PipelineRun.id).label(
                    "failure_count"
                ),
            )
            .where(
                PipelineRun.status == "FAILED",
                PipelineRun.error_category.is_not(None),
            )
            .group_by(
                PipelineRun.error_category
            )
            .order_by(
                desc("failure_count")
            )
            .limit(limit)
        )

        rows = session.execute(query).all()

        return [
            {
                "error_category": row.error_category,
                "failure_count": row.failure_count,
            }
            for row in rows
        ]

    except SQLAlchemyError:
        logger.exception(
            "Failed to calculate error-category statistics."
        )
        raise

    finally:
        session.close()


def get_recent_pipeline_runs(
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Retrieve recent pipeline runs for analytical context.
    """

    session = SessionLocal()

    try:
        query = (
            select(PipelineRun)
            .order_by(
                desc(PipelineRun.start_time)
            )
            .limit(limit)
        )

        runs = session.scalars(query).all()

        return [
            {
                "run_id": run.run_id,
                "pipeline_name": run.pipeline_name,
                "status": run.status,
                "duration_seconds": run.duration_seconds,
                "error_category": run.error_category,
                "sla_breach_seconds": run.sla_breach_seconds,
                "start_time": (
                    run.start_time.isoformat()
                    if run.start_time
                    else None
                ),
            }
            for run in runs
        ]

    except SQLAlchemyError:
        logger.exception(
            "Failed to retrieve recent pipeline runs."
        )
        raise

    finally:
        session.close()


@tool(
    "get_pipeline_statistics",
    args_schema=PipelineStatsInput,
)
def pipeline_statistics_tool(
    pipeline_name: str,
) -> dict[str, Any]:
    """
    Return aggregated operational statistics for one pipeline.
    """

    return get_pipeline_statistics(
        pipeline_name=pipeline_name,
    )


@tool(
    "get_error_category_statistics",
    args_schema=ErrorCategoryStatsInput,
)
def error_category_statistics_tool(
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Return failure counts grouped by error category.
    """

    return get_error_category_statistics(
        limit=limit,
    )


@tool(
    "get_recent_pipeline_runs",
    args_schema=RecentRunsInput,
)
def recent_pipeline_runs_tool(
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Return the most recent pipeline executions.
    """

    return get_recent_pipeline_runs(
        limit=limit,
    )


SQL_TOOLS = [
    pipeline_statistics_tool,
    error_category_statistics_tool,
    recent_pipeline_runs_tool,
]