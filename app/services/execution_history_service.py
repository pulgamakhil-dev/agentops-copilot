from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.database import SessionLocal
from app.db.models import ExecutionRecord


logger = get_logger(__name__)


class ExecutionHistoryService:
    """
    Provides read-only access to persisted execution records.
    """

    def get_by_execution_id(
        self,
        execution_id: str,
        session: Session | None = None,
    ) -> ExecutionRecord | None:
        """
        Retrieve a single execution using its execution ID.
        """

        owns_session = session is None
        db = session or SessionLocal()

        try:
            return (
                db.query(ExecutionRecord)
                .filter(
                    ExecutionRecord.execution_id == execution_id
                )
                .first()
            )
        finally:
            if owns_session:
                db.close()

    def get_by_approval_id(
        self,
        approval_id: str,
        session: Session | None = None,
    ) -> ExecutionRecord | None:
        """
        Retrieve the execution associated with an approval.
        """

        owns_session = session is None
        db = session or SessionLocal()

        try:
            return (
                db.query(ExecutionRecord)
                .filter(
                    ExecutionRecord.approval_id == approval_id
                )
                .first()
            )
        finally:
            if owns_session:
                db.close()

    def list_executions(
        self,
        limit: int = 20,
        offset: int = 0,
        session: Session | None = None,
    ) -> tuple[list[ExecutionRecord], int]:
        """
        Retrieve execution history using pagination.

        Returns:
        A tuple containing the execution records
        and the total number of available records.
        """

        owns_session = session is None
        db = session or SessionLocal()

        try:
            # Count all records so the API can expose
            # pagination metadata to clients.
            total = db.query(ExecutionRecord).count()

            # Newest executions are returned first.
            records = (
                db.query(ExecutionRecord)
                .order_by(ExecutionRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return records, total

        finally:
            if owns_session:
                db.close()
    def list_executions(
        self,
        offset: int = 0,
        limit: int = 20,
        session: Session | None = None,
    ) -> tuple[list[ExecutionRecord], int]:
        """
    Retrieve execution records using offset-based pagination.

    Returns both the requested records and the total number
    of execution records available.
    """

        owns_session = session is None
        db = session or SessionLocal()

        try:
            # Build the base query once so filtering can be
            # extended later without duplicating query logic.
            query = db.query(ExecutionRecord)

            total = query.count()

            records = (
                query
                .order_by(ExecutionRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            return records, total

        finally:
            if owns_session:
                db.close()


# Shared read-only execution history service.
execution_history_service = ExecutionHistoryService()