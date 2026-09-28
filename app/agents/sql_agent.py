from typing import Annotated, TypedDict

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_ollama import ChatOllama
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import get_settings
from app.core.logging import get_logger
from app.tools.sql_tools import SQL_TOOLS


logger = get_logger(__name__)


class SQLAgentState(TypedDict):
    """
    State shared across the SQL Agent graph.

    add_messages preserves the full conversation and tool history
    while LangGraph moves between the model and tool nodes.
    """

    messages: Annotated[list[AnyMessage], add_messages]


class SQLAgent:
    """
    LangGraph-based analytical agent for pipeline operational data.

    The agent can perform only approved, read-only analytical queries
    exposed through SQL_TOOLS.
    """

    def __init__(self) -> None:
        settings = get_settings()

        # Initialize the configured local LLM.
        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=0,
        )

        # Restrict the model to approved analytical tools only.
        self.llm_with_tools = self.llm.bind_tools(
            SQL_TOOLS
        )

        self.system_prompt = """
You are the SQL Analytics Agent for AgentOps Copilot.

Your role is to analyze pipeline execution data using only the
approved analytical tools available to you.

You may:
- calculate statistics for a specific pipeline
- analyze failure categories
- inspect recent pipeline activity

Rules:
- Use tools when data is required.
- Never invent statistics, counts, failure rates, or execution data.
- Never execute arbitrary SQL.
- Never modify data.
- Never perform INSERT, UPDATE, DELETE, DROP, ALTER, or similar actions.
- Base all conclusions on retrieved tool results.
- If the available tools cannot answer the question, clearly say so.
- Keep answers concise, factual, and operationally useful.
"""

        self.graph = self._build_graph()

    def _call_model(
        self,
        state: SQLAgentState,
    ) -> dict:
        """
        Invoke the LLM using the current graph state.
        """

        messages = [
            SystemMessage(content=self.system_prompt),
            *state["messages"],
        ]

        response = self.llm_with_tools.invoke(messages)

        return {
            "messages": [response]
        }

    def _build_graph(self):
        """
        Build the SQL Agent workflow.

        Flow:
        START -> agent -> tools -> agent -> final response
        """

        builder = StateGraph(SQLAgentState)

        builder.add_node(
            "agent",
            self._call_model,
        )

        builder.add_node(
            "tools",
            ToolNode(SQL_TOOLS),
        )

        builder.add_edge(
            START,
            "agent",
        )

        builder.add_conditional_edges(
            "agent",
            tools_condition,
        )

        builder.add_edge(
            "tools",
            "agent",
        )

        return builder.compile()

    def invoke(
        self,
        user_query: str,
    ) -> str:
        """
        Execute the SQL analytical workflow and return
        the final model response.
        """

        logger.info(
            "SQL Agent received request | query=%s",
            user_query,
        )

        result = self.graph.invoke(
            {
                "messages": [
                    HumanMessage(content=user_query)
                ]
            }
        )

        final_message = result["messages"][-1]

        return final_message.content