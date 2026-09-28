from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


VIEWER_HEADERS = {
    "X-User-ID": "agent-viewer-001",
    "X-Username": "agent-viewer",
    "X-User-Roles": "viewer",
}

OPERATOR_HEADERS = {
    "X-User-ID": "agent-operator-001",
    "X-Username": "agent-operator",
    "X-User-Roles": "operator",
}


def test_agent_query_requires_authentication() -> None:
    response = client.post(
        "/api/v1/agent/query",
        json={
            "query": "Rerun customer_ingestion."
        },
    )

    assert response.status_code == 401


def test_viewer_cannot_request_action() -> None:
    with patch(
        "app.agents.supervisor.SupervisorAgent.route"
    ) as mock_route:
        from app.agents.supervisor import SupervisorDecision

        mock_route.return_value = SupervisorDecision(
            agent="action",
            reason="User explicitly requested a pipeline rerun.",
        )

        response = client.post(
            "/api/v1/agent/query",
            json={
                "query": "Rerun customer_ingestion."
            },
            headers=VIEWER_HEADERS,
        )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "REQUEST_ACTION permission is required."
    )


def test_operator_identity_reaches_action_agent() -> None:
    with (
        patch(
            "app.agents.supervisor.SupervisorAgent.route"
        ) as mock_route,
        patch(
            "app.agents.supervisor.ActionAgent.invoke"
        ) as mock_action,
    ):
        from app.agents.supervisor import SupervisorDecision

        mock_route.return_value = SupervisorDecision(
            agent="action",
            reason="User explicitly requested a pipeline rerun.",
        )

        mock_action.return_value = {
            "approval_id": "approval-security-test",
            "pipeline_name": "customer_ingestion",
            "action": "rerun_pipeline",
            "risk": "approval_required",
            "status": "pending",
            "requested_by": "agent-operator",
            "message": (
                "Pipeline rerun was not executed. "
                "Human approval is required."
            ),
        }

        response = client.post(
            "/api/v1/agent/query",
            json={
                "query": "Rerun customer_ingestion."
            },
            headers=OPERATOR_HEADERS,
        )

    assert response.status_code == 200

    mock_action.assert_called_once_with(
        "Rerun customer_ingestion.",
        requested_by="agent-operator",
    )

    data = response.json()

    assert data["metadata"]["requested_by"] == "agent-operator"
    assert data["metadata"]["status"] == "pending"