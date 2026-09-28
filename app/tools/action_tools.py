from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.action_service import action_service


logger = get_logger(__name__)


class RerunPipelineInput(BaseModel):
    """
    Validated input for requesting a pipeline rerun.

    This tool does not execute the rerun. It creates a human
    approval request for the proposed action.
    """

    pipeline_name: str = Field(
        ...,
        min_length=1,
        description="Pipeline proposed for rerun.",
    )

    reason: str = Field(
        ...,
        min_length=5,
        description=(
            "Operational reason for requesting the rerun."
        ),
    )

    requested_by: str = Field(
        default="agentops_copilot",
        min_length=1,
        description=(
            "Trusted application identity requesting the action. "
            "This value must not be inferred from the user prompt."
        ),
    )


@tool(
    "request_pipeline_rerun",
    args_schema=RerunPipelineInput,
)
def request_pipeline_rerun_tool(
    pipeline_name: str,
    reason: str,
    requested_by: str = "agentops_copilot",
) -> dict[str, Any]:
    """
    Request human approval for rerunning a pipeline.

    This tool never executes the pipeline rerun directly.
    The requester identity is propagated into the approval
    and audit workflow.
    """

    approval = action_service.request_action(
        action_name="rerun_pipeline",
        reason=reason,
        resource_type="pipeline",
        resource_name=pipeline_name,
        requested_by=requested_by,
    )

    logger.info(
        "Pipeline rerun approval created | "
        "pipeline=%s | approval_id=%s | requested_by=%s",
        pipeline_name,
        approval.approval_id,
        requested_by,
    )

    return {
        "approval_id": approval.approval_id,
        "pipeline_name": pipeline_name,
        "action": approval.action_name,
        "risk": approval.action_risk.value,
        "status": approval.status.value,
        "requested_by": requested_by,
        "message": (
            "Pipeline rerun was not executed. "
            "Human approval is required."
        ),
    }


ACTION_TOOLS = [
    request_pipeline_rerun_tool,
]