from app.core.guardrails import (
    ActionRisk,
    classify_action,
)
from app.core.logging import get_logger
from app.models.approval import ApprovalRequest
from app.services.approval_service import approval_service


logger = get_logger(__name__)


class ActionService:
    """
    Controls requests for operational actions.

    Read-only actions must use their approved tool paths.
    Risky actions create approval requests instead of executing.
    Blocked actions are rejected completely.

    Requester identity is supplied by the trusted application layer
    and propagated into the approval and audit workflow.
    """

    def request_action(
        self,
        action_name: str,
        reason: str,
        resource_type: str | None = None,
        resource_name: str | None = None,
        requested_by: str = "agentops_copilot",
    ) -> ApprovalRequest:
        """
        Validate an operational action and create an approval request.

        This method never executes state-changing operations directly.
        """

        risk = classify_action(action_name)

        logger.info(
            "Operational action requested | "
            "action=%s | risk=%s | resource_type=%s | "
            "resource_name=%s | requested_by=%s",
            action_name,
            risk.value,
            resource_type,
            resource_name,
            requested_by,
        )

        if risk == ActionRisk.READ_ONLY:
            raise ValueError(
                "Read-only actions should use their approved tool."
            )

        return approval_service.create_request(
            action_name=action_name,
            reason=reason,
            resource_type=resource_type,
            resource_name=resource_name,
            requested_by=requested_by,
        )


action_service = ActionService()