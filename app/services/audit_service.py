from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.database import SessionLocal
from app.db.models import AuditEvent


logger = get_logger(__name__)


class AuditService:
    """
    Provides centralized persistence for AgentOps audit events.

    Domain services use this service to record security-sensitive
    activity without depending directly on the audit table.
    """

    def record_event(
        self,
        event_type: str,
        actor: str,
        action_name: str | None = None,
        resource_type: str | None = None,
        resource_name: str | None = None,
        approval_id: str | None = None,
        execution_id: str | None = None,
        outcome: str | None = None,
        message: str | None = None,
        session: Session | None = None,
    ) -> AuditEvent:
        """
        Persist a single immutable audit event.
        """

        owns_session = session is None
        db = session or SessionLocal()

        try:
            event = AuditEvent(
                event_id=str(uuid4()),
                event_type=event_type,
                actor=actor,
                action_name=action_name,
                resource_type=resource_type,
                resource_name=resource_name,
                approval_id=approval_id,
                execution_id=execution_id,
                outcome=outcome,
                message=message,
            )

            db.add(event)

            if owns_session:
                db.commit()
                db.refresh(event)
            else:
                # Make the insert part of the caller's transaction.
                db.flush()

            logger.info(
                "Audit event recorded | "
                "event_id=%s | event_type=%s | actor=%s | "
                "approval_id=%s | execution_id=%s",
                event.event_id,
                event.event_type,
                event.actor,
                event.approval_id,
                event.execution_id,
            )

            return event

        except Exception:
            if owns_session:
                db.rollback()

            logger.exception(
                "Unable to record audit event | "
                "event_type=%s | actor=%s",
                event_type,
                actor,
            )

            raise

        finally:
            if owns_session:
                db.close()


audit_service = AuditService()