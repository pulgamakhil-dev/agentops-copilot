from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.authorization import require_permission
from app.core.logging import get_logger
from app.core.permissions import Permission
from app.core.security import UserIdentity
from app.models.execution import (
    ExecutionHistoryResponse,
    ExecutionRecordResponse,
)
from app.services.execution_history_service import (
    execution_history_service,
)
from app.services.execution_service import execution_service


logger = get_logger(__name__)

router = APIRouter(
    prefix="/executions",
    tags=["Executions"],
)


@router.post("/{approval_id}")
def execute_approved_action(
    approval_id: str,
    current_user: UserIdentity = Depends(
        require_permission(Permission.EXECUTE_ACTION)
    ),
):
    """
    Execute an action that has already received human approval.

    Authentication and RBAC are enforced before this endpoint
    is allowed to call the controlled execution service.
    """

    try:
        result = execution_service.execute_approved_action(
            approval_id=approval_id,
            executed_by=current_user.username,
)

        # Record the authenticated actor in application logs.
        logger.info(
            "Controlled execution completed | "
            "approval_id=%s | execution_id=%s | actor=%s",
            approval_id,
            result.execution_id,
            current_user.username,
        )

        return result

    except PermissionError as exc:
        # Approval exists but is not authorized for execution.
        logger.warning(
            "Execution denied | approval_id=%s | actor=%s | reason=%s",
            approval_id,
            current_user.username,
            str(exc),
        )

        raise HTTPException(
            status_code=403,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        # Handles unsupported actions, invalid resources,
        # and duplicate execution attempts.
        logger.warning(
            "Execution rejected | approval_id=%s | actor=%s | reason=%s",
            approval_id,
            current_user.username,
            str(exc),
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Do not expose unexpected internal exception details.
        logger.exception(
            "Controlled execution failed | "
            "approval_id=%s | actor=%s",
            approval_id,
            current_user.username,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to execute approved action.",
        ) from exc
@router.get(
    "/history",
    response_model=ExecutionHistoryResponse,
)
def list_execution_history(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of execution records to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of execution records to skip.",
    ),
    current_user: UserIdentity = Depends(
        require_permission(
            Permission.VIEW_EXECUTION_HISTORY
        )
    ),
):
    """
    Retrieve execution history using offset-based pagination.

    Authentication and VIEW_EXECUTION_HISTORY permission
    are required. This endpoint is read-only.
    """

    try:
        records, total = execution_history_service.list_executions(
            offset=offset,
            limit=limit,
        )

        logger.info(
            "Execution history listed | "
            "actor=%s | limit=%s | offset=%s | total=%s",
            current_user.username,
            limit,
            offset,
            total,
        )

        return {
            "items": [
                ExecutionRecordResponse.model_validate(record)
                for record in records
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as exc:
        logger.exception(
            "Unable to list execution history | actor=%s",
            current_user.username,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve execution history.",
        ) from exc

@router.get(
    "/history/by-approval/{approval_id}",
    response_model=ExecutionRecordResponse,
)
def get_execution_history_by_approval(
    approval_id: str,
    current_user: UserIdentity = Depends(
        require_permission(
            Permission.VIEW_EXECUTION_HISTORY
        )
    ),
) -> ExecutionRecordResponse:
    """
    Retrieve the execution associated with an approval ID.

    This is a read-only operation protected by the
    VIEW_EXECUTION_HISTORY permission.
    """

    try:
        record = execution_history_service.get_by_approval_id(
            approval_id
        )

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Execution record not found for this approval.",
            )

        logger.info(
            "Execution history retrieved | "
            "approval_id=%s | actor=%s",
            approval_id,
            current_user.username,
        )

        return ExecutionRecordResponse.model_validate(record)

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unable to retrieve execution history | "
            "approval_id=%s | actor=%s",
            approval_id,
            current_user.username,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve execution history.",
        ) from exc


@router.get(
    "/history/{execution_id}",
    response_model=ExecutionRecordResponse,
)
def get_execution_history(
    execution_id: str,
    current_user: UserIdentity = Depends(
        require_permission(
            Permission.VIEW_EXECUTION_HISTORY
        )
    ),
) -> ExecutionRecordResponse:
    """
    Retrieve a persisted execution record by execution ID.

    This endpoint is read-only and cannot trigger or modify
    pipeline execution.
    """

    try:
        record = execution_history_service.get_by_execution_id(
            execution_id
        )

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Execution record not found.",
            )

        logger.info(
            "Execution history retrieved | "
            "execution_id=%s | actor=%s",
            execution_id,
            current_user.username,
        )

        return ExecutionRecordResponse.model_validate(record)

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unable to retrieve execution history | "
            "execution_id=%s | actor=%s",
            execution_id,
            current_user.username,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve execution history.",
        ) from exc