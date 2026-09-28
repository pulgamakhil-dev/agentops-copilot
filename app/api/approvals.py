from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authorization import require_permission
from app.core.logging import get_logger
from app.core.permissions import Permission
from app.core.security import UserIdentity
from app.models.approval import (
    ApprovalDecision,
    ApprovalRequest,
)
from app.services.approval_service import approval_service


logger = get_logger(__name__)


router = APIRouter(
    prefix="/api/v1/approvals",
    tags=["approvals"],
)


@router.get(
    "/{approval_id}",
    response_model=ApprovalRequest,
)
def get_approval(
    approval_id: str,
) -> ApprovalRequest:
    """
    Retrieve an approval request by ID.
    """

    try:
        request = approval_service.get_request(
            approval_id
        )

        return request

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{approval_id}/decision",
    response_model=ApprovalRequest,
)
def decide_approval(
    approval_id: str,
    decision: ApprovalDecision,
    current_user: UserIdentity = Depends(
        require_permission(Permission.APPROVE_ACTION)
    ),
) -> ApprovalRequest:
    """
    Approve or reject a pending AgentOps action.

    The reviewer identity is derived from the authenticated
    user rather than trusted from the incoming request body.
    """

    if approval_id != decision.approval_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Approval ID in the URL does not match "
                "the request payload."
            ),
        )

    # Never trust the reviewer identity supplied by the client.
    # Bind the decision to the authenticated application user.
    authenticated_decision = ApprovalDecision(
        approval_id=decision.approval_id,
        approved=decision.approved,
        reviewer=current_user.username,
        comment=decision.comment,
    )

    try:
        result = approval_service.decide(
            authenticated_decision
        )

        logger.info(
            "Approval decision completed | "
            "approval_id=%s | reviewer=%s | status=%s",
            result.approval_id,
            current_user.username,
            result.status.value,
        )

        return result

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        logger.warning(
            "Approval decision rejected | "
            "approval_id=%s | reviewer=%s | reason=%s",
            approval_id,
            current_user.username,
            str(exc),
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc