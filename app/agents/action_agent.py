from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.tools.action_tools import request_pipeline_rerun_tool


logger = get_logger(__name__)


class PipelineRerunRequest(BaseModel):
    """
    Structured interpretation of a pipeline rerun request.

    The model extracts only the information needed to create
    a controlled approval request.
    """

    pipeline_name: str = Field(
        ...,
        min_length=1,
        description="Name of the pipeline the user wants to rerun.",
    )

    reason: str = Field(
        ...,
        min_length=5,
        description=(
            "Clear operational reason for requesting the pipeline rerun."
        ),
    )


class ActionAgent:
    """
    Handles controlled state-changing requests.

    This agent never executes a production action directly.
    It converts the user's request into a validated approval request.
    """

    def __init__(self) -> None:
        settings = get_settings()

        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=0,
        )

        # Structured output prevents us from manually parsing
        # free-form LLM text.
        self.action_parser = self.llm.with_structured_output(
            PipelineRerunRequest
        )

        self.system_prompt = """
You are the Action Agent for AgentOps Copilot.

Your responsibility is to interpret explicit requests for controlled
operational actions.

Currently supported action:
- request a pipeline rerun

Rules:
- Extract the exact pipeline name from the user request.
- Create a concise operational reason.
- Do not claim that the pipeline was rerun.
- Do not execute any production action.
- The actual action requires human approval.
- If the request is ambiguous, do not invent a pipeline name.
"""

    def parse_request(
        self,
        user_query: str,
    ) -> PipelineRerunRequest:
        """
        Convert a natural-language action request into
        validated structured data.
        """

        logger.info(
            "Action Agent received request | query=%s",
            user_query,
        )

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_query),
        ]

        return self.action_parser.invoke(messages)

    def invoke(
        self,
        user_query: str,
        requested_by: str = "agentops_copilot",
    ) -> dict:
        """
        Create a human approval request for the proposed action.

        The LLM extracts only operational request data.
        Requester identity comes from the trusted application layer.

        No pipeline execution occurs here.
        """

        parsed_request = self.parse_request(
            user_query
        )

        logger.info(
            "Action Agent parsed rerun request | "
            "pipeline=%s | requested_by=%s",
            parsed_request.pipeline_name,
            requested_by,
        )

        result = request_pipeline_rerun_tool.invoke(
            {
                "pipeline_name": parsed_request.pipeline_name,
                "reason": parsed_request.reason,
                "requested_by": requested_by,
           }
        )

        return result