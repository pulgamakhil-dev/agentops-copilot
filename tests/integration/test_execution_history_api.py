from fastapi.testclient import TestClient

from app.main import app
from app.models.approval import ApprovalDecision
from app.services.approval_service import approval_service
from app.services.execution_service import execution_service


client = TestClient(app)


# Authentication headers used by read-only execution-history tests.
# The viewer role has VIEW_EXECUTION_HISTORY permission.
VIEWER_HEADERS = {
    "X-User-ID": "integration-viewer-001",
    "X-Username": "integration-viewer",
    "X-User-Roles": "viewer",
}


def create_completed_execution():
    """
    Create, approve, and execute a pipeline action.

    This helper gives the integration tests a real persisted
    execution record that can be retrieved through the API.
    """

    approval = approval_service.create_request(
        action_name="rerun_pipeline",
        reason="Integration test execution.",
        resource_type="pipeline",
        resource_name="customer_ingestion",
    )

    approval_service.decide(
        ApprovalDecision(
            approval_id=approval.approval_id,
            approved=True,
            reviewer="integration-test",
            comment="Approved for integration testing.",
        )
    )

    result = execution_service.execute_approved_action(
        approval_id=approval.approval_id,
        executed_by="integration-executor",
    )

    return approval, result


def test_get_execution_by_id():
    """
    Verify execution history can be retrieved
    using the execution ID.
    """

    approval, result = create_completed_execution()

    response = client.get(
        f"/executions/history/{result.execution_id}",
        headers=VIEWER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["execution_id"] == result.execution_id
    assert data["approval_id"] == approval.approval_id
    assert data["action_name"] == "rerun_pipeline"
    assert data["resource_name"] == "customer_ingestion"


def test_get_execution_by_approval_id():
    """
    Verify execution history can be retrieved
    using its approval ID.
    """

    approval, result = create_completed_execution()

    response = client.get(
        f"/executions/history/by-approval/{approval.approval_id}",
        headers=VIEWER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["execution_id"] == result.execution_id
    assert data["approval_id"] == approval.approval_id
    assert data["action_name"] == "rerun_pipeline"
    assert data["resource_name"] == "customer_ingestion"


def test_execution_history_pagination():
    """
    Verify the execution-history endpoint respects
    limit and offset parameters.
    """

    create_completed_execution()

    response = client.get(
        "/executions/history",
        params={
            "limit": 5,
            "offset": 0,
        },
        headers=VIEWER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

    assert data["limit"] == 5
    assert data["offset"] == 0

    # The endpoint must never return more records
    # than the requested page size.
    assert len(data["items"]) <= 5

    # At least the execution created above should exist.
    assert data["total"] >= 1


def test_execution_history_invalid_limit():
    """
    Verify FastAPI rejects pagination values
    outside the allowed API contract.
    """

    response = client.get(
        "/executions/history",
        params={
            "limit": 101,
            "offset": 0,
        },
        headers=VIEWER_HEADERS,
    )

    # Query validation should reject limit > 100.
    assert response.status_code == 422


def test_execution_history_negative_offset():
    """
    Verify negative offsets are rejected.
    """

    response = client.get(
        "/executions/history",
        params={
            "limit": 5,
            "offset": -1,
        },
        headers=VIEWER_HEADERS,
    )

    assert response.status_code == 422

def test_execution_history_returns_executed_by():
    """
    Verify the authenticated execution identity is persisted
    and exposed through the execution-history API.
    """

    approval, result = create_completed_execution()

    response = client.get(
        f"/executions/history/{result.execution_id}",
        headers=VIEWER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["execution_id"] == result.execution_id
    assert data["approval_id"] == approval.approval_id
    assert data["executed_by"] == "integration-executor"