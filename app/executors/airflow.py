from uuid import uuid4

from app.clients.airflow_client import AirflowClient
from app.core.logging import get_logger
from app.executors.base import ActionExecutor, ExecutionResult


logger = get_logger(__name__)


class AirflowActionExecutor(ActionExecutor):
    """
    Executes approved pipeline reruns through Apache Airflow.

    All HTTP communication is delegated to AirflowClient so the
    executor remains focused on operational execution behavior.
    """

    def __init__(
        self,
        client: AirflowClient,
    ) -> None:
        self.client = client

    def rerun_pipeline(
        self,
        pipeline_name: str,
    ) -> ExecutionResult:
        """
        Trigger an approved Airflow DAG run.

        The pipeline name is treated as the Airflow DAG identifier.
        """

        if not pipeline_name.strip():
            raise ValueError(
                "Pipeline name cannot be empty."
            )

        logger.info(
            "Triggering approved Airflow DAG | dag_id=%s",
            pipeline_name,
        )

        response = self.client.trigger_dag(
            dag_id=pipeline_name,
        )

        # Prefer Airflow's DAG run identifier when available.
        execution_id = (
            response.get("dag_run_id")
            or response.get("run_id")
            or str(uuid4())
        )

        return ExecutionResult(
            success=True,
            execution_id=execution_id,
            action_name="rerun_pipeline",
            resource_name=pipeline_name,
            status=response.get("state", "submitted"),
            message=(
                f"Airflow DAG run submitted for {pipeline_name}."
            ),
            metadata={
                "executor": "airflow",
                "dag_id": pipeline_name,
            },
        )