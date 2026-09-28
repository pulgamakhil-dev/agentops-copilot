from typing import Optional

from sqlalchemy import Select, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import PipelineRun


logger = get_logger(__name__)


class MonitoringService:
    """
    Service layer for reading pipeline execution data.

    This keeps database access separate from API routes and AI agents.
    Agents should call this service instead of writing SQL directly.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_failed_runs(
        self,
        limit: int = 20,
        pipeline_name: Optional[str] = None,
    ) -> list[PipelineRun]:
        """
        Return the most recent failed pipeline executions.

        An optional pipeline name can be provided to filter results.
        """

        try:
            query: Select = (
                select(PipelineRun)
                .where(PipelineRun.status == "FAILED")
                .order_by(desc(PipelineRun.start_time))
                .limit(limit)
            )

            if pipeline_name:
                query = query.where(
                    PipelineRun.pipeline_name == pipeline_name
                )

            return list(
                self.session.scalars(query).all()
            )

        except SQLAlchemyError:
            logger.exception(
                "Failed to retrieve failed pipeline runs."
            )
            raise

    def get_pipeline_history(
        self,
        pipeline_name: str,
        limit: int = 20,
    ) -> list[PipelineRun]:
        """
        Return recent execution history for a specific pipeline.
        """

        try:
            query = (
                select(PipelineRun)
                .where(
                    PipelineRun.pipeline_name == pipeline_name
                )
                .order_by(desc(PipelineRun.start_time))
                .limit(limit)
            )

            return list(
                self.session.scalars(query).all()
            )

        except SQLAlchemyError:
            logger.exception(
                "Failed to retrieve pipeline history."
            )
            raise

    def get_incident_runs(
        self,
        incident_id: str,
    ) -> list[PipelineRun]:
        """
        Return every pipeline execution associated with an incident.

        This is useful for tracking the original failure and later retries.
        """

        try:
            query = (
                select(PipelineRun)
                .where(
                    PipelineRun.incident_id == incident_id
                )
                .order_by(PipelineRun.start_time)
            )

            return list(
                self.session.scalars(query).all()
            )

        except SQLAlchemyError:
            logger.exception(
                "Failed to retrieve incident history."
            )
            raise

    def get_sla_breaches(
        self,
        limit: int = 20,
    ) -> list[PipelineRun]:
        """
        Return pipeline runs that exceeded their configured SLA.
        """

        try:
            query = (
                select(PipelineRun)
                .where(
                    PipelineRun.sla_breach_seconds > 0
                )
                .order_by(
                    desc(PipelineRun.sla_breach_seconds)
                )
                .limit(limit)
            )

            return list(
                self.session.scalars(query).all()
            )

        except SQLAlchemyError:
            logger.exception(
                "Failed to retrieve SLA breaches."
            )
            raise

    def get_run_by_id(
        self,
        run_id: str,
    ) -> Optional[PipelineRun]:
        """
        Return one pipeline execution by its unique run ID.
        """

        try:
            query = (
                select(PipelineRun)
                .where(
                    PipelineRun.run_id == run_id
                )
            )

            return self.session.scalar(query)

        except SQLAlchemyError:
            logger.exception(
                "Failed to retrieve pipeline run."
            )
            raise