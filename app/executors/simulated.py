from uuid import uuid4

from app.core.logging import get_logger
from app.executors.base import ActionExecutor, ExecutionResult


logger = get_logger(__name__)


class SimulatedActionExecutor(ActionExecutor):
    """
    Safe local executor for development and testing.

    This executor simulates operational actions without connecting
    to or modifying any real production infrastructure.
    """

    def rerun_pipeline(
        self,
        pipeline_name: str,
    ) -> ExecutionResult:
        """
        Simulate an approved pipeline rerun.

        No external orchestration platform is called.
        """

        if not pipeline_name.strip():
            raise ValueError(
                "Pipeline name cannot be empty."
            )

        execution_id = str(uuid4())

        logger.info(
            "Simulating pipeline rerun | "
            "pipeline=%s | execution_id=%s",
            pipeline_name,
            execution_id,
        )

        return ExecutionResult(
            success=True,
            execution_id=execution_id,
            action_name="rerun_pipeline",
            resource_name=pipeline_name,
            status="simulated",
            message=(
                f"Pipeline rerun simulated successfully for "
                f"{pipeline_name}. No production action was executed."
            ),
            metadata={
                "executor": "simulated",
            },
        )