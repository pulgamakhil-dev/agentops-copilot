from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import AuditEvent
from app.services.audit_service import audit_service


def test_record_audit_event() -> None:
    event = audit_service.record_event(
        event_type="TEST_EVENT",
        actor="test-user",
        action_name="test_action",
        resource_type="pipeline",
        resource_name="test-pipeline",
        approval_id="approval-test-audit",
        execution_id="execution-test-audit",
        outcome="completed",
        message="Audit service test event.",
    )

    assert event.event_id is not None
    assert event.event_type == "TEST_EVENT"
    assert event.actor == "test-user"
    assert event.action_name == "test_action"
    assert event.resource_type == "pipeline"
    assert event.resource_name == "test-pipeline"
    assert event.approval_id == "approval-test-audit"
    assert event.execution_id == "execution-test-audit"
    assert event.outcome == "completed"
    assert event.message == "Audit service test event."

    session = SessionLocal()

    try:
        stored_event = session.scalar(
            select(AuditEvent).where(
                AuditEvent.event_id == event.event_id
            )
        )

        assert stored_event is not None
        assert stored_event.event_type == "TEST_EVENT"
        assert stored_event.actor == "test-user"
        assert stored_event.action_name == "test_action"
        assert stored_event.resource_type == "pipeline"
        assert stored_event.resource_name == "test-pipeline"
        assert stored_event.approval_id == "approval-test-audit"
        assert stored_event.execution_id == "execution-test-audit"
        assert stored_event.outcome == "completed"
        assert stored_event.message == "Audit service test event."

    finally:
        session.close()