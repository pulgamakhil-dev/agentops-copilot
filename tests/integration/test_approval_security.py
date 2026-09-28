from fastapi.testclient import TestClient

from app.main import app
from app.services.approval_service import approval_service


client = TestClient(app)


def test_approval_requires_approver_permission() -> None:
    """
    An operator must not be allowed to approve
    an operational action.
    """

    approval = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Testing approval RBAC.",
        resource_type="pipeline",
        resource_name="customer_ingestion",
        requested_by="requester-001",
    )

    headers = {
        "X-User-ID": "operator-002",
        "X-Username": "test-operator",
        "X-User-Roles": "operator",
    }

    response = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        headers=headers,
        json={
            "approval_id": approval.approval_id,
            "approved": True,
            "reviewer": "fake-approver",
            "comment": "Attempting approval.",
        },
    )

    assert response.status_code == 403
    assert "approve_action" in response.json()["detail"]


def test_authenticated_reviewer_cannot_be_spoofed() -> None:
    """
    Reviewer identity must come from authentication,
    not from the client-supplied request body.
    """

    approval = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Testing authenticated reviewer identity.",
        resource_type="pipeline",
        resource_name="customer_ingestion",
        requested_by="requester-002",
    )

    headers = {
        "X-User-ID": "approver-001",
        "X-Username": "authenticated-approver",
        "X-User-Roles": "approver",
    }

    response = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        headers=headers,
        json={
            "approval_id": approval.approval_id,
            "approved": True,
            "reviewer": "spoofed-reviewer",
            "comment": "Approved after review.",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "approved"
    assert response_data["reviewer"] == "authenticated-approver"
    assert response_data["reviewer"] != "spoofed-reviewer"

    stored = approval_service.get_request(
        approval.approval_id
    )

    assert stored.reviewer == "authenticated-approver"

def test_requester_cannot_bypass_self_approval_with_spoofed_reviewer() -> None:
    """
    A requester must not be able to approve their own request
    by supplying a different reviewer identity in the payload.
    """

    approval = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Testing self-approval bypass protection.",
        resource_type="pipeline",
        resource_name="customer_ingestion",
        requested_by="same-user",
    )

    headers = {
        "X-User-ID": "approver-002",
        "X-Username": "same-user",
        "X-User-Roles": "approver",
    }

    response = client.post(
        f"/api/v1/approvals/{approval.approval_id}/decision",
        headers=headers,
        json={
            "approval_id": approval.approval_id,
            "approved": True,
            "reviewer": "different-fake-user",
            "comment": "Trying to bypass self-approval protection.",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Requester cannot review their own approval request."
    )

    stored = approval_service.get_request(
        approval.approval_id
    )

    assert stored.status.value == "pending"
    assert stored.reviewer is None
    assert stored.decided_at is None