from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from pydantic import BaseModel, Field, field_validator
from app.core.logging import get_logger
from app.rag.retriever import RunbookRetriever


logger = get_logger(__name__)

# Load the retriever once so the FAISS index and embedding model
# are not reloaded for every tool call.
retriever = RunbookRetriever()


class RunbookSearchInput(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        description="Operational issue or troubleshooting question.",
    )

    k: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Maximum number of runbook passages.",
    )

    @field_validator("k", mode="before")
    @classmethod
    def normalize_k(cls, value):
        if isinstance(value, dict):
            value = value.get("value", value)

        return value
    
def search_runbooks(
    query: str,
    k: int = 4,
) -> list[dict[str, Any]]:
    """
    Search the local troubleshooting knowledge base.

    The function is read-only and returns retrieved runbook evidence
    together with source filenames.
    """

    try:
        return retriever.search(
            query=query,
            k=k,
        )

    except Exception:
        logger.exception(
            "Runbook search failed."
        )
        raise


@tool(
    "search_runbooks",
    args_schema=RunbookSearchInput,
)
def search_runbooks_tool(
    query: str,
    k: int = 4,
) -> list[dict[str, Any]]:
    """
    Search troubleshooting runbooks for operational guidance.

    Use this tool when you need documented investigation steps,
    root-cause possibilities, remediation guidance, validation steps,
    or escalation procedures.
    """

    return search_runbooks(
        query=query,
        k=k,
    )


RAG_TOOLS = [
    search_runbooks_tool,
]