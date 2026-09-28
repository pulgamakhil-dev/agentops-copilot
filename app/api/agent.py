from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.supervisor import SupervisorAgent
from app.core.auth import get_current_user
from app.core.logging import get_logger
from app.core.security import UserIdentity
from app.models.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
)


logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["agent"],
)


# Initialize once and reuse across requests.
# This avoids repeatedly loading the LLM and vector store.
supervisor = SupervisorAgent()


@router.post(
    "/query",
    response_model=AgentQueryResponse,
)
def query_agent(
    request: AgentQueryRequest,
    current_user: UserIdentity = Depends(get_current_user),
) -> AgentQueryResponse:
    """
    Process an authenticated AgentOps Copilot request.

    Authenticated identity is supplied by the application security
    layer and is never derived from the user's natural-language prompt.
    """

    logger.info(
        "Agent query received | query=%s | user=%s",
        request.query,
        current_user.username,
    )

    try:
        result = supervisor.invoke(
        request.query,            
        current_user=current_user,
        )

        # Preserve structured action information such as
        # approval ID, approval status, and requester identity.
        if isinstance(result, dict):
            return AgentQueryResponse(
                response=result.get(
                    "message",
                    "Controlled action request created.",
                ),
                metadata=result,
            )

        return AgentQueryResponse(
            response=result,
        )

    except PermissionError as exc:
        logger.warning(
            "Agent action authorization denied | user=%s",
            current_user.username,
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Agent query processing failed | user=%s",
            current_user.username,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process agent request.",
        ) from exc