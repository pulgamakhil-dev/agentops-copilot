from typing import Annotated, TypedDict

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import get_settings
from app.core.logging import get_logger
from app.tools.monitoring_tools import MONITORING_TOOLS


logger = get_logger(__name__)


class MonitoringState(TypedDict):
    """
    State shared between nodes in the Monitoring Agent graph.

    add_messages tells LangGraph to append new messages instead
    of replacing the existing conversation history.
    """

    messages: Annotated[list[AnyMessage], add_messages]


class MonitoringAgent:
    """
    LangGraph-based agent for investigating pipeline operations.

    The graph allows the LLM to select approved monitoring tools,
    execute them, inspect their results, and produce a grounded answer.
    """

    def __init__(self) -> None:
        settings = get_settings()

        # Model configuration comes from environment-based settings.
        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=0,
        )

        # The model can see only explicitly approved read-only tools.
        self.llm_with_tools = self.llm.bind_tools(
            MONITORING_TOOLS
        )

        self.system_prompt = """
You are the Monitoring Agent for AgentOps Copilot.

Investigate data pipeline operational issues using the approved
monitoring tools available to you.

You may:
- inspect failed pipeline runs
- review pipeline execution history
- inspect incident history
- review SLA breaches

Rules:
- Use tools whenever operational evidence is required.
- Never invent pipeline runs, incidents, errors, or metrics.
- Never modify pipeline or database state.
- Do not execute remediation actions.
- Base conclusions only on retrieved evidence.
- Clearly distinguish evidence from conclusions.
- If evidence is insufficient, say so.
- Keep operational findings concise and actionable.
"""

        # Build the graph once when the agent is initialized.
        self.graph = self._build_graph()

    def _call_model(
        self,
        state: MonitoringState,
    ) -> dict:
        """
        Invoke the LLM using the current conversation state.
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
        Construct and compile the Monitoring Agent workflow.

        Flow:
        START -> agent -> tools -> agent -> END

        tools_condition automatically decides whether the model
        requested a tool or is ready to return its final response.
        """

        builder = StateGraph(MonitoringState)

        builder.add_node(
            "agent",
            self._call_model,
        )

        builder.add_node(
            "tools",
            ToolNode(MONITORING_TOOLS),
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
        Execute the complete monitoring workflow and return
        the final grounded response.
        """

        logger.info(
            "Monitoring Agent received request | query=%s",
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