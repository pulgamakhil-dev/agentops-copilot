from fastapi.testclient import TestClient
from unittest.mock import patch

from app.executors.base import ExecutionResult
from app.services.execution_service import execution_service
from app.main import app


client = TestClient(app)


def test_execution_requires_authentication() -> None:
    """
    Requests without authentication headers must be rejected.
    """

    response = client.post(
        "/executions/test-approval-id"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication credentials are required."
    )


def test_viewer_cannot_execute_action() -> None:
    """
    A viewer is authenticated but does not have
    permission to execute approved actions.
    """

    headers = {
        "X-User-ID": "user-viewer-001",
        "X-Username": "test-viewer",
        "X-User-Roles": "viewer",
    }

    response = client.post(
        "/executions/test-approval-id",
        headers=headers,
    )

    assert response.status_code == 403
    assert "execute_action" in response.json()["detail"]


def test_invalid_role_is_rejected() -> None:
    """
    Authentication must reject unknown roles.
    """

    headers = {
        "X-User-ID": "user-001",
        "X-Username": "test-user",
        "X-User-Roles": "superuser",
    }

    response = client.post(
        "/executions/test-approval-id",
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid user role."


def test_operator_passes_rbac_check() -> None:
    """
    An operator should pass authentication and RBAC.

    The fake approval ID does not exist, so the request may
    fail later in the execution service. The important check
    here is that authentication does not return 401 or 403.
    """

    headers = {
        "X-User-ID": "user-operator-001",
        "X-Username": "test-operator",
        "X-User-Roles": "operator",
    }

    response = client.post(
        "/executions/nonexistent-approval-id",
        headers=headers,
    )

    # Authentication and RBAC must have succeeded.
    assert response.status_code not in {401, 403}


def test_execution_history_requires_authentication() -> None:
    """
    Execution history must not be available anonymously.
    """

    response = client.get(
        "/executions/history/nonexistent-execution-id"
    )

    assert response.status_code == 401


def test_viewer_can_access_execution_history() -> None:
    """
    Viewer has read-only execution-history permission.

    The record does not exist, so 404 proves the request
    successfully passed authentication and authorization.
    """

    headers = {
        "X-User-ID": "user-viewer-002",
        "X-Username": "history-viewer",
        "X-User-Roles": "viewer",
    }

    response = client.get(
        "/executions/history/nonexistent-execution-id",
        headers=headers,
    )

    assert response.status_code == 404

def test_authenticated_executor_identity_is_forwarded() -> None:
    """
    The execution endpoint must derive the executor identity
    from the authenticated user and pass it to the execution
    service for persistent audit logging.
    """

    headers = {
        "X-User-ID": "user-operator-002",
        "X-Username": "execution-operator",
        "X-User-Roles": "operator",
    }

    fake_result = ExecutionResult(
        success=True,
        execution_id="execution-test-001",
        action_name="rerun_pipeline",
        resource_name="daily-orders-pipeline",
        status="completed",
        message="Pipeline rerun completed.",
        metadata={},
    )

    with patch.object(
        execution_service,
        "execute_approved_action",
        return_value=fake_result,
    ) as mocked_execute:
        response = client.post(
            "/executions/approval-test-001",
            headers=headers,
        )

    assert response.status_code == 200

    mocked_execute.assert_called_once_with(
        approval_id="approval-test-001",
        executed_by="execution-operator",
    )