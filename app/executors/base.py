from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionResult:
    """
    Standard result returned by every operational executor.

    Keeping a common result format allows AgentOps Copilot to switch
    execution providers without changing the agent or service layers.
    """

    success: bool
    execution_id: str
    action_name: str
    resource_name: str
    status: str
    message: str
    metadata: dict[str, Any] | None = None


class ActionExecutor(ABC):
    """
    Provider-independent interface for controlled operational actions.

    Implementations may later support systems such as Airflow,
    Databricks, or other orchestration platforms.
    """

    @abstractmethod
    def rerun_pipeline(
        self,
        pipeline_name: str,
    ) -> ExecutionResult:
        """
        Execute an approved pipeline rerun.

        Implementations must return a standardized ExecutionResult.
        """
        raise NotImplementedError