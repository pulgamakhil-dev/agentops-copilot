from uuid import uuid4

from sqlalchemy import select

from app.agents.action_agent import ActionAgent
from app.db.database import SessionLocal
from app.db.models import ApprovalRecord, AuditEvent


def test_action_agent_persists_authenticated_requester_identity() -> None:
    """
    Verify that trusted requester identity is persisted through the
    complete controlled-action workflow.

    The LLM is bypassed here so this test focuses only on identity
    propagation, approval persistence, and auditing.
    """

    pipeline_name = f"identity-test-pipeline-{uuid4().hex}"
    requested_by = f"identity-test-operator-{uuid4().hex}"

    agent = ActionAgent()

    # Bypass LLM parsing so the integration test remains deterministic.
    from app.agents.action_agent import PipelineRerunRequest

    agent.parse_request = lambda user_query: PipelineRerunRequest(
        pipeline_name=pipeline_name,
        reason="Validate authenticated requester identity propagation.",
    )

    result = agent.invoke(
        f"Rerun {pipeline_name}.",
        requested_by=requested_by,
    )

    approval_id = result["approval_id"]

    assert result["requested_by"] == requested_by
    assert result["status"] == "pending"

    session = SessionLocal()

    try:
        approval = session.scalar(
            select(ApprovalRecord).where(
                ApprovalRecord.approval_id == approval_id
            )
        )

        assert approval is not None
        assert approval.requested_by == requested_by
        assert approval.resource_type == "pipeline"
        assert approval.resource_name == pipeline_name

        audit_event = session.scalar(
            select(AuditEvent).where(
                AuditEvent.approval_id == approval_id,
                AuditEvent.event_type == "ACTION_REQUESTED",
            )
        )

        assert audit_event is not None
        assert audit_event.actor == requested_by
        assert audit_event.resource_type == "pipeline"
        assert audit_event.resource_name == pipeline_name

    finally:
        session.close()