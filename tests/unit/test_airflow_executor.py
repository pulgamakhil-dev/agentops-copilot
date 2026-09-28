from unittest.mock import Mock

from app.executors.airflow import AirflowActionExecutor


def test_airflow_rerun_pipeline() -> None:
    """
    Verify that the Airflow executor triggers the expected DAG
    and converts the Airflow response into ExecutionResult.
    """

    # Mock the Airflow client so this test makes no network request.
    mock_client = Mock()

    mock_client.trigger_dag.return_value = {
        "dag_run_id": "manual__2026-09-15T12:00:00",
        "state": "queued",
    }

    executor = AirflowActionExecutor(
        client=mock_client
    )

    result = executor.rerun_pipeline(
        "customer_ingestion"
    )

    # Verify the correct DAG was requested.
    mock_client.trigger_dag.assert_called_once_with(
        dag_id="customer_ingestion"
    )

    # Verify Airflow's response is mapped correctly.
    assert result.success is True
    assert result.execution_id == (
        "manual__2026-09-15T12:00:00"
    )
    assert result.action_name == "rerun_pipeline"
    assert result.resource_name == "customer_ingestion"
    assert result.status == "queued"
    assert result.metadata == {
        "executor": "airflow",
        "dag_id": "customer_ingestion",
    }