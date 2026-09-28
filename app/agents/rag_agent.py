
import json
import re
from typing import Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from app.core.config import get_settings
from app.core.logging import get_logger
from app.tools.rag_tools import RAG_TOOLS, search_runbooks


logger = get_logger(__name__)


class RAGAgent:
    """
    Runbook RAG agent with:
    - LangGraph tool-calling workflow
    - FAISS-backed runbook retrieval
    - Pipeline-specific evidence validation
    - Structured evaluation output
    """

    def __init__(self):
        settings = get_settings()

        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=0,
        )

        self.llm_with_tools = self.llm.bind_tools(RAG_TOOLS)

        self.system_prompt = """
You are the Runbook RAG Agent for AgentOps Copilot.

Your responsibility is to answer operational questions using
retrieved runbook documentation.

GENERAL RULES:
1. Use the search_runbooks tool to retrieve relevant evidence.
2. Ground operational procedures in retrieved documentation.
3. Never invent runbook steps, incident history, or configurations.
4. Clearly identify the runbook supporting your answer.
5. If documentation is missing, explicitly acknowledge the gap.
6. Never disclose secrets, credentials, or private personal data.
7. Never execute production changes or pipeline reruns.
8. Production actions require authorization and human approval.

ANSWER COMPLETENESS:
When the user asks for a troubleshooting or recovery procedure,
include the documented:
- Symptoms, when relevant
- Investigation steps
- Recommended remediation
- Approval requirements
- Validation after recovery
- Escalation conditions, when relevant

If the retrieved evidence contains only part of the procedure,
search again for the missing sections.

Do not tell the user to search for remediation or validation
when those sections have already been retrieved.

PIPELINE-SPECIFIC DOCUMENTATION:
A general incident runbook does not automatically constitute
a documented procedure for a particular pipeline.

Only describe a procedure as pipeline-specific when the
retrieved evidence explicitly establishes that relationship.

When no pipeline-specific documentation exists, say so.
You may provide general guidance, clearly labeled as general.

SAFETY:
Never independently restart or rerun a production pipeline.
Explain required approval and post-recovery validation instead.

Keep answers accurate, structured, and practical.
"""

        graph = StateGraph(MessagesState)

        graph.add_node("agent", self._call_model)
        graph.add_node("tools", ToolNode(RAG_TOOLS))

        graph.add_edge(START, "agent")

        graph.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {
                "tools": "tools",
                "end": END,
            },
        )

        graph.add_edge("tools", "agent")

        self.graph = graph.compile()

    def _call_model(self, state: MessagesState) -> dict:
        messages = [
            SystemMessage(content=self.system_prompt),
            *state["messages"],
        ]

        response = self.llm_with_tools.invoke(messages)

        return {"messages": [response]}

    @staticmethod
    def _route_after_agent(state: MessagesState) -> str:
        last_message = state["messages"][-1]

        if isinstance(last_message, AIMessage):
            if last_message.tool_calls:
                return "tools"

        return "end"

    @staticmethod
    def _extract_pipeline_name(query: str) -> str | None:
        """
        Recognize named pipelines in recovery-procedure questions.

        Examples:
        - documented recovery procedure for customer_ingestion
        - recovery steps for orders_pipeline

        This is a conservative preliminary extractor.
        A production system should use a pipeline registry.
        """
        query_lower = query.lower()

        recovery_terms = (
            "recovery",
            "recover",
            "remediation",
            "restart",
            "rerun",
            "procedure",
        )

        if not any(term in query_lower for term in recovery_terms):
            return None

        patterns = [
            r"\b(?:procedure|recovery|remediation|steps)"
            r"\s+(?:for|of)\s+"
            r"([a-zA-Z][a-zA-Z0-9_]*)",

            r"\b(?:restart|rerun|recover)\s+"
            r"(?:the\s+)?"
            r"([a-zA-Z][a-zA-Z0-9_]*)",
        ]

        general_terms = {
            "api",
            "timeouts",
            "timeout",
            "schema",
            "drift",
            "spark",
            "memory",
            "pipeline",
            "pipelines",
            "failed",
            "failure",
            "failures",
            "production",
            "service",
            "services",
        }

        for pattern in patterns:
            match = re.search(
                pattern,
                query,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            name = match.group(1)

            if name.lower() in general_terms:
                continue

            # Underscore-separated identifiers are a useful
            # signal for the current dataset's pipeline names.
            if "_" in name:
                return name

        return None

    @staticmethod
    def _contains_exact_name(
        content: str,
        pipeline_name: str,
    ) -> bool:
        pattern = (
            rf"(?<![a-zA-Z0-9_])"
            rf"{re.escape(pipeline_name)}"
            rf"(?![a-zA-Z0-9_])"
        )

        return bool(
            re.search(
                pattern,
                content,
                flags=re.IGNORECASE,
            )
        )

    def _check_pipeline_documentation(
        self,
        query: str,
    ) -> dict[str, Any] | None:
        """
        Check whether retrieved runbook passages explicitly
        mention the requested pipeline.

        Returns None for ordinary questions or when evidence
        explicitly names the pipeline.

        Returns an abstention result when no matching evidence
        is found.
        """
        pipeline_name = self._extract_pipeline_name(query)

        if pipeline_name is None:
            return None

        logger.info(
            "Checking documentation for pipeline: %s",
            pipeline_name,
        )

        evidence = search_runbooks(
            query=f"{pipeline_name} recovery procedure",
            k=10,
        )

        matching_evidence = [
            item
            for item in evidence
            if self._contains_exact_name(
                item.get("content", ""),
                pipeline_name,
            )
        ]

        if matching_evidence:
            return None

        answer = (
            "I could not find a documented recovery procedure "
            f"specifically for {pipeline_name}. "
            "The available runbooks provide general guidance "
            "for incidents such as API timeouts, schema drift, "
            "and Spark memory failures, but the retrieved "
            "documentation does not establish which procedure "
            "applies to this pipeline."
        )

        return {
            "query": query,
            "answer": answer,
            "tool_calls": [
                {
                    "name": "search_runbooks",
                    "args": {
                        "query": (
                            f"{pipeline_name} recovery procedure"
                        ),
                        "k": 10,
                    },
                }
            ],
            "retrieved_evidence": evidence,
            "retrieval_performed": True,
        }

    @staticmethod
    def _parse_tool_evidence(
        content: Any,
    ) -> list[dict[str, Any]]:
        """
        Normalize tool results into individual evidence records.

        Handles:
        - JSON-serialized lists
        - JSON-serialized dictionaries
        - Existing Python lists and dictionaries
        """
        if isinstance(content, list):
            # Some LangChain versions return text blocks.
            if content and all(
                isinstance(item, dict)
                and item.get("type") == "text"
                for item in content
            ):
                records = []

                for item in content:
                    records.extend(
                        RAGAgent._parse_tool_evidence(
                            item.get("text", "")
                        )
                    )

                return records

            return [
                item
                for item in content
                if isinstance(item, dict)
                and "content" in item
            ]

        if isinstance(content, dict):
            if "content" in content:
                return [content]

            return []

        if not isinstance(content, str):
            return []

        try:
            parsed = json.loads(content)
        except (ValueError, TypeError):
            return []

        return RAGAgent._parse_tool_evidence(parsed)

    @staticmethod
    def _extract_answer(messages: list) -> str:
        for message in reversed(messages):
            if not isinstance(message, AIMessage):
                continue

            if message.tool_calls:
                continue

            content = message.content

            if isinstance(content, str):
                return content

            if isinstance(content, list):
                return "\n".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict)
                    and item.get("type") == "text"
                )

        return "No final answer was generated."

    def _run(self, query: str) -> dict[str, Any]:
        if not isinstance(query, str):
            raise TypeError(
                "RAGAgent query must be a string."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "RAGAgent query cannot be empty."
            )

        # Run the deterministic safeguard before invoking
        # the LLM. Both public methods use this shared path.
        safeguard_result = (
            self._check_pipeline_documentation(query)
        )

        if safeguard_result is not None:
            return safeguard_result

        result = self.graph.invoke(
            {
                "messages": [
                    HumanMessage(content=query),
                ]
            },
            config={
                "recursion_limit": 12,
            },
        )

        messages = result["messages"]

        tool_calls = []
        retrieved_evidence = []

        for message in messages:
            if isinstance(message, AIMessage):
                for call in message.tool_calls:
                    tool_calls.append(
                        {
                            "name": call.get("name"),
                            "args": call.get("args", {}),
                        }
                    )

            elif isinstance(message, ToolMessage):
                if message.name == "search_runbooks":
                    retrieved_evidence.extend(
                        self._parse_tool_evidence(
                            message.content
                        )
                    )

        return {
            "query": query,
            "answer": self._extract_answer(messages),
            "tool_calls": tool_calls,
            "retrieved_evidence": retrieved_evidence,
            "retrieval_performed": bool(
                retrieved_evidence
            ),
        }

    def invoke(self, query: str) -> str:
        """
        Return the agent's final answer.
        """
        return self._run(query)["answer"]

    def invoke_for_evaluation(
        self,
        query: str,
    ) -> dict[str, Any]:
        """
        Return the answer, tool calls, and evidence
        for the RAG evaluation runner.
        """
        return self._run(query)