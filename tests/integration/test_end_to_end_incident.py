
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import AuditEvent, ExecutionRecord
from app.executors.base import ExecutionResult
from app.models.approval import ApprovalDecision, ApprovalStatus
from app.services.approval_service import approval_service
from app.services.execution_service import execution_service


def test_controlled_pipeline_rerun_end_to_end() -> None:
    pipeline = "e2e_test_pipeline"

    # 1. An operator requests a controlled pipeline rerun.
    request = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Pipeline failure requires investigation and a controlled rerun.",
        resource_type="pipeline",
        resource_name=pipeline,
        requested_by="e2e-operator",
    )

    assert request.status == ApprovalStatus.PENDING

    # 2. Execution must be blocked before human approval.
    with pytest.raises(PermissionError):
        execution_service.execute_approved_action(
            approval_id=request.approval_id,
            executed_by="e2e-executor",
        )

    # 3. A different person approves the request.
    decision = ApprovalDecision(
        approval_id=request.approval_id,
        approved=True,
        reviewer="e2e-reviewer",
        comment="Investigation reviewed. Controlled rerun approved.",
    )

    approved = approval_service.decide(decision)

    assert approved.status == ApprovalStatus.APPROVED
    assert approved.reviewer == "e2e-reviewer"

    # 4. Mock the external executor. No real pipeline is rerun.
    fake_provider_result = ExecutionResult(
        success=True,
        execution_id="mock-provider-run-001",
        action_name="rerun_pipeline",
        resource_name=pipeline,
        status="completed",
        message="Mocked pipeline rerun completed.",
        metadata={"mocked": True},
    )

    with patch.object(
        execution_service.executor,
        "rerun_pipeline",
        return_value=fake_provider_result,
    ) as mock_rerun:

        result = execution_service.execute_approved_action(
            approval_id=request.approval_id,
            executed_by="e2e-executor",
        )

        mock_rerun.assert_called_once_with(pipeline)

        assert result.success is True
        assert result.status == "completed"
        assert result.metadata["provider_execution_id"] == (
            "mock-provider-run-001"
        )

        # 5. The same approval cannot trigger another execution.
        with pytest.raises(
            ValueError,
            match="already been submitted",
        ):
            execution_service.execute_approved_action(
                approval_id=request.approval_id,
                executed_by="e2e-executor",
            )

        mock_rerun.assert_called_once()

    # 6. Verify the persisted execution and complete audit trail.
    with SessionLocal() as session:
        record = session.scalar(
            select(ExecutionRecord).where(
                ExecutionRecord.approval_id == request.approval_id
            )
        )

        assert record is not None
        assert record.execution_id == result.execution_id
        assert record.executed_by == "e2e-executor"
        assert record.status == "completed"

        events = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.approval_id == request.approval_id)
            .order_by(AuditEvent.created_at)
        ).all()

        assert [event.event_type for event in events] == [
            "ACTION_REQUESTED",
            "APPROVAL_GRANTED",
            "EXECUTION_STARTED",
            "EXECUTION_COMPLETED",
        ]

        assert [event.actor for event in events] == [
            "e2e-operator",
            "e2e-reviewer",
            "e2e-executor",
            "e2e-executor",
        ]

        assert all(
            event.resource_name == pipeline
            for event in events
        )

        assert events[2].execution_id == result.execution_id
        assert events[3].execution_id == result.execution_id