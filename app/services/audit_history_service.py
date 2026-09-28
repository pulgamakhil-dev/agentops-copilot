from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import AuditEvent
from app.models.audit import AuditHistoryResponse


class AuditHistoryService:
    """
    Provides read-only access to persisted audit events.

    Supports pagination and optional filtering while keeping audit
    event creation separate from audit-history querying.
    """

    def list_events(
        self,
        limit: int = 50,
        offset: int = 0,
        event_type: str | None = None,
        actor: str | None = None,
        approval_id: str | None = None,
        execution_id: str | None = None,
        resource_type: str | None = None,
        resource_name: str | None = None,
    ) -> AuditHistoryResponse:
        session: Session = SessionLocal()

        try:
            filters = []

            if event_type:
                filters.append(AuditEvent.event_type == event_type)

            if actor:
                filters.append(AuditEvent.actor == actor)

            if approval_id:
                filters.append(AuditEvent.approval_id == approval_id)

            if execution_id:
                filters.append(AuditEvent.execution_id == execution_id)

            if resource_type:
                filters.append(AuditEvent.resource_type == resource_type)

            if resource_name:
                filters.append(AuditEvent.resource_name == resource_name)

            count_query = select(func.count()).select_from(AuditEvent)

            events_query = select(AuditEvent)

            if filters:
                count_query = count_query.where(*filters)
                events_query = events_query.where(*filters)

            total = session.scalar(count_query) or 0

            events = session.scalars(
                events_query
                .order_by(AuditEvent.created_at.desc())
                .limit(limit)
                .offset(offset)
            ).all()

            return AuditHistoryResponse(
                items=events,
                total=total,
                limit=limit,
                offset=offset,
            )

        finally:
            session.close()


audit_history_service = AuditHistoryService()