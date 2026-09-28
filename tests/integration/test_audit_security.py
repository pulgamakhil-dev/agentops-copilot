from fastapi.testclient import TestClient
from app.services.audit_service import audit_service
from app.main import app
from uuid import uuid4


client = TestClient(app)


VIEWER_HEADERS = {
    "X-User-ID": "audit-viewer-001",
    "X-Username": "audit-viewer",
    "X-User-Roles": "viewer",
}

OPERATOR_HEADERS = {
    "X-User-ID": "audit-operator-001",
    "X-Username": "audit-operator",
    "X-User-Roles": "operator",
}

APPROVER_HEADERS = {
    "X-User-ID": "audit-approver-001",
    "X-Username": "audit-approver",
    "X-User-Roles": "approver",
}

ADMIN_HEADERS = {
    "X-User-ID": "audit-admin-001",
    "X-Username": "audit-admin",
    "X-User-Roles": "admin",
}


def test_audit_history_requires_authentication() -> None:
    response = client.get("/audit/history")

    assert response.status_code == 401


def test_viewer_cannot_access_audit_history() -> None:
    response = client.get(
        "/audit/history",
        headers=VIEWER_HEADERS,
    )

    assert response.status_code == 403


def test_operator_cannot_access_audit_history() -> None:
    response = client.get(
        "/audit/history",
        headers=OPERATOR_HEADERS,
    )

    assert response.status_code == 403


def test_approver_can_access_audit_history() -> None:
    response = client.get(
        "/audit/history",
        headers=APPROVER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


def test_admin_can_access_audit_history() -> None:
    response = client.get(
        "/audit/history",
        headers=ADMIN_HEADERS,
    )

    assert response.status_code == 200

def test_audit_history_filters_by_event_type() -> None:
    audit_service.record_event(
        event_type="FILTER_TEST_EVENT",
        actor="filter-test-user",
        action_name="rerun_pipeline",
        resource_type="pipeline",
        resource_name="filter-test-pipeline",
        outcome="completed",
        message="Event type filter test.",
    )

    response = client.get(
        "/audit/history",
        params={"event_type": "FILTER_TEST_EVENT"},
        headers=APPROVER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    for event in data["items"]:
        assert event["event_type"] == "FILTER_TEST_EVENT"


def test_audit_history_filters_by_actor() -> None:
    audit_service.record_event(
        event_type="ACTOR_FILTER_TEST",
        actor="unique-filter-actor",
        action_name="rerun_pipeline",
        resource_type="pipeline",
        resource_name="actor-filter-pipeline",
        outcome="completed",
        message="Actor filter test.",
    )

    response = client.get(
        "/audit/history",
        params={"actor": "unique-filter-actor"},
        headers=APPROVER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for event in data["items"]:
        assert event["actor"] == "unique-filter-actor"


def test_audit_history_filters_by_approval_id() -> None:
    audit_service.record_event(
        event_type="APPROVAL_FILTER_TEST",
        actor="filter-test-user",
        approval_id="unique-filter-approval-id",
        outcome="approved",
        message="Approval ID filter test.",
    )

    response = client.get(
        "/audit/history",
        params={"approval_id": "unique-filter-approval-id"},
        headers=APPROVER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for event in data["items"]:
        assert event["approval_id"] == "unique-filter-approval-id"


def test_audit_history_filters_by_execution_id() -> None:
    audit_service.record_event(
        event_type="EXECUTION_FILTER_TEST",
        actor="filter-test-user",
        execution_id="unique-filter-execution-id",
        outcome="completed",
        message="Execution ID filter test.",
    )

    response = client.get(
        "/audit/history",
        params={"execution_id": "unique-filter-execution-id"},
        headers=APPROVER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for event in data["items"]:
        assert event["execution_id"] == "unique-filter-execution-id"


def test_audit_history_filters_by_resource() -> None:
    audit_service.record_event(
        event_type="RESOURCE_FILTER_TEST",
        actor="filter-test-user",
        resource_type="pipeline",
        resource_name="unique-resource-pipeline",
        outcome="completed",
        message="Resource filter test.",
    )

    response = client.get(
        "/audit/history",
        params={
            "resource_type": "pipeline",
            "resource_name": "unique-resource-pipeline",
        },
        headers=APPROVER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for event in data["items"]:
        assert event["resource_type"] == "pipeline"
        assert event["resource_name"] == "unique-resource-pipeline"

def test_audit_history_supports_combined_filters() -> None:
    audit_service.record_event(
        event_type="COMBINED_FILTER_TEST",
        actor="combined-filter-user",
        action_name="rerun_pipeline",
        resource_type="pipeline",
        resource_name="combined-filter-pipeline",
        approval_id="combined-filter-approval",
        outcome="completed",
        message="Combined filter test.",
    )

    response = client.get(
        "/audit/history",
        params={
            "event_type": "COMBINED_FILTER_TEST",
            "actor": "combined-filter-user",
            "resource_type": "pipeline",
            "resource_name": "combined-filter-pipeline",
        },
        headers=APPROVER_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1

    for event in data["items"]:
        assert event["event_type"] == "COMBINED_FILTER_TEST"
        assert event["actor"] == "combined-filter-user"
        assert event["resource_type"] == "pipeline"
        assert event["resource_name"] == "combined-filter-pipeline"


def test_audit_history_pagination() -> None:
    pagination_actor = f"pagination-test-{uuid4()}"

    for index in range(3):
        audit_service.record_event(
            event_type="PAGINATION_TEST",
            actor=pagination_actor,
            action_name="rerun_pipeline",
            resource_type="pipeline",
            resource_name=f"pagination-pipeline-{index}",
            outcome="completed",
            message=f"Pagination test event {index}.",
        )

    first_page = client.get(
        "/audit/history",
        params={
            "actor": pagination_actor,
            "limit": 2,
            "offset": 0,
        },
        headers=APPROVER_HEADERS,
    )

    assert first_page.status_code == 200

    first_data = first_page.json()

    assert first_data["total"] == 3
    assert first_data["limit"] == 2
    assert first_data["offset"] == 0
    assert len(first_data["items"]) == 2

    second_page = client.get(
        "/audit/history",
        params={
            "actor": pagination_actor,
            "limit": 2,
            "offset": 2,
        },
        headers=APPROVER_HEADERS,
    )

    assert second_page.status_code == 200

    second_data = second_page.json()

    assert second_data["total"] == 3
    assert second_data["limit"] == 2
    assert second_data["offset"] == 2
    assert len(second_data["items"]) == 1