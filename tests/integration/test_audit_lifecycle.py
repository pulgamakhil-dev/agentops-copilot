from sqlalchemy import select
from unittest.mock import patch
from app.db.database import SessionLocal
from app.db.models import AuditEvent
from app.models.approval import ApprovalDecision
from app.services.approval_service import approval_service
from app.services.execution_service import execution_service


def test_approval_lifecycle_creates_audit_events() -> None:
    request = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Pipeline failed and requires a controlled rerun.",
        resource_type="pipeline",
        resource_name="audit-test-pipeline",
        requested_by="audit-requester",
    )

    decision = ApprovalDecision(
        approval_id=request.approval_id,
        approved=True,
        reviewer="audit-reviewer",
        comment="Approved for audit lifecycle test.",
    )

    approval_service.decide(decision)

    session = SessionLocal()

    try:
        events = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.approval_id == request.approval_id)
            .order_by(AuditEvent.created_at)
        ).all()

        assert len(events) == 2

        requested_event = events[0]
        approved_event = events[1]

        assert requested_event.event_type == "ACTION_REQUESTED"
        assert requested_event.actor == "audit-requester"
        assert requested_event.action_name == "rerun_pipeline"
        assert requested_event.resource_type == "pipeline"
        assert requested_event.resource_name == "audit-test-pipeline"
        assert requested_event.approval_id == request.approval_id

        assert approved_event.event_type == "APPROVAL_GRANTED"
        assert approved_event.actor == "audit-reviewer"
        assert approved_event.action_name == "rerun_pipeline"
        assert approved_event.resource_type == "pipeline"
        assert approved_event.resource_name == "audit-test-pipeline"
        assert approved_event.approval_id == request.approval_id

    finally:
        session.close()

def test_execution_lifecycle_creates_audit_events() -> None:
    request = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Pipeline requires a controlled rerun.",
        resource_type="pipeline",
        resource_name="audit-execution-pipeline",
        requested_by="audit-requester",
    )

    decision = ApprovalDecision(
        approval_id=request.approval_id,
        approved=True,
        reviewer="audit-reviewer",
        comment="Approved for execution lifecycle test.",
    )

    approval_service.decide(decision)

    result = execution_service.execute_approved_action(
        approval_id=request.approval_id,
        executed_by="audit-executor",
    )

    session = SessionLocal()

    try:
        events = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.approval_id == request.approval_id)
            .order_by(AuditEvent.created_at)
        ).all()

        event_types = [event.event_type for event in events]

        assert event_types == [
            "ACTION_REQUESTED",
            "APPROVAL_GRANTED",
            "EXECUTION_STARTED",
            "EXECUTION_COMPLETED",
        ]

        started_event = events[2]

        assert started_event.actor == "audit-executor"
        assert started_event.execution_id == result.execution_id
        assert started_event.action_name == "rerun_pipeline"
        assert started_event.resource_type == "pipeline"
        assert started_event.resource_name == "audit-execution-pipeline"
        assert started_event.outcome == "started"

        completed_event = events[3]

        assert completed_event.actor == "audit-executor"
        assert completed_event.execution_id == result.execution_id
        assert completed_event.approval_id == request.approval_id
        assert completed_event.action_name == "rerun_pipeline"
        assert completed_event.resource_type == "pipeline"
        assert completed_event.resource_name == "audit-execution-pipeline"
        assert completed_event.outcome == result.status

    finally:
        session.close()

def test_rejected_approval_creates_audit_event() -> None:
    request = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Pipeline rerun requested.",
        resource_type="pipeline",
        resource_name="audit-rejection-pipeline",
        requested_by="audit-requester",
    )

    decision = ApprovalDecision(
        approval_id=request.approval_id,
        approved=False,
        reviewer="audit-reviewer",
        comment="Rejected during audit lifecycle test.",
    )

    approval_service.decide(decision)

    session = SessionLocal()

    try:
        events = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.approval_id == request.approval_id)
            .order_by(AuditEvent.created_at)
        ).all()

        assert len(events) == 2

        assert events[0].event_type == "ACTION_REQUESTED"
        assert events[0].actor == "audit-requester"

        assert events[1].event_type == "APPROVAL_REJECTED"
        assert events[1].actor == "audit-reviewer"
        assert events[1].outcome == "rejected"
        assert events[1].message == "Rejected during audit lifecycle test."

    finally:
        session.close()

def test_failed_execution_creates_audit_event() -> None:
    request = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Pipeline requires a controlled rerun.",
        resource_type="pipeline",
        resource_name="audit-failure-pipeline",
        requested_by="audit-requester",
    )

    decision = ApprovalDecision(
        approval_id=request.approval_id,
        approved=True,
        reviewer="audit-reviewer",
        comment="Approved for failure-path test.",
    )

    approval_service.decide(decision)

    with patch.object(
        execution_service.executor,
        "rerun_pipeline",
        side_effect=RuntimeError("Simulated executor failure."),
    ):
        try:
            execution_service.execute_approved_action(
                approval_id=request.approval_id,
                executed_by="audit-executor",
            )
        except RuntimeError:
            pass

    session = SessionLocal()

    try:
        events = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.approval_id == request.approval_id)
            .order_by(AuditEvent.created_at)
        ).all()

        event_types = [event.event_type for event in events]

        assert event_types == [
            "ACTION_REQUESTED",
            "APPROVAL_GRANTED",
            "EXECUTION_STARTED",
            "EXECUTION_FAILED",
        ]

        failed_event = events[-1]

        assert failed_event.actor == "audit-executor"
        assert failed_event.action_name == "rerun_pipeline"
        assert failed_event.resource_type == "pipeline"
        assert failed_event.resource_name == "audit-failure-pipeline"
        assert failed_event.approval_id == request.approval_id
        assert failed_event.execution_id is not None
        assert failed_event.outcome == "failed"
        assert failed_event.message == "Simulated executor failure."

    finally:
        session.close()