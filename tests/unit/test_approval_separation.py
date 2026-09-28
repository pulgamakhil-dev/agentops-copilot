import pytest

from app.models.approval import ApprovalDecision, ApprovalStatus
from app.services.approval_service import approval_service


def test_requester_cannot_approve_own_request() -> None:
    """
    Verify separation of duties prevents a requester
    from approving their own operational action.
    """

    approval = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Testing separation of duties.",
        resource_type="pipeline",
        resource_name="customer_ingestion",
        requested_by="operator-001",
    )

    decision = ApprovalDecision(
        approval_id=approval.approval_id,
        approved=True,
        reviewer="operator-001",
        comment="Attempting self-approval.",
    )

    with pytest.raises(
        ValueError,
        match="Requester cannot review their own approval request",
    ):
        approval_service.decide(decision)

    # Failed self-approval must not change the persisted state.
    stored = approval_service.get_request(
        approval.approval_id
    )

    assert stored.status == ApprovalStatus.PENDING
    assert stored.reviewer is None
    assert stored.decided_at is None


def test_different_reviewer_can_approve_request() -> None:
    """
    Verify a different reviewer can approve
    the request successfully.
    """

    approval = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Testing valid independent approval.",
        resource_type="pipeline",
        resource_name="customer_ingestion",
        requested_by="operator-001",
    )

    decision = ApprovalDecision(
        approval_id=approval.approval_id,
        approved=True,
        reviewer="approver-001",
        comment="Reviewed and approved.",
    )

    result = approval_service.decide(decision)

    assert result.status == ApprovalStatus.APPROVED
    assert result.requested_by == "operator-001"
    assert result.reviewer == "approver-001"
    assert result.decided_at is not None