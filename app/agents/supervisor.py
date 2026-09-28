
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.agents.action_agent import ActionAgent
from app.agents.investigation_agent import InvestigationAgent
from app.agents.monitoring_agent import MonitoringAgent
from app.agents.rag_agent import RAGAgent
from app.agents.sql_agent import SQLAgent
from app.core.action_intent import is_advice_request
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.permissions import Permission, has_permission
from app.core.security import UserIdentity


logger = get_logger(__name__)


class SupervisorDecision(BaseModel):
    """
    Structured routing decision produced by the Supervisor.

    The Supervisor selects only one approved specialist agent.
    """

    agent: Literal[
        "monitoring",
        "sql",
        "rag",
        "investigation",
        "action",
    ] = Field(
        ...,
        description="Specialist agent that should handle the request.",
    )

    reason: str = Field(
        ...,
        min_length=1,
        description="Short explanation for why this agent was selected.",
    )


class SupervisorAgent:
    """
    Routes AgentOps Copilot requests to specialist agents.

    The Supervisor does not perform operational actions itself.
    It selects the appropriate agent and enforces authorization
    before forwarding action requests.
    """

    def __init__(self) -> None:
        settings = get_settings()

        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=0,
        )

        # Force routing decisions into a validated schema.
        self.router_llm = self.llm.with_structured_output(
            SupervisorDecision
        )

        # Initialize specialist agents once and reuse them.
        self.monitoring_agent = MonitoringAgent()
        self.sql_agent = SQLAgent()
        self.rag_agent = RAGAgent()
        self.action_agent = ActionAgent()
        self.investigation_agent = InvestigationAgent()

        self.system_prompt = """
You are the Supervisor Agent for AgentOps Copilot.

Your only responsibility is to route the user's request to the
most appropriate specialist agent.

Available agents:

investigation:
Use when the user's request requires both observed operational
evidence and troubleshooting or remediation guidance.

Use this route for compound incident questions such as:
- Why something failed and what should be done next.
- What happened and how to fix it.
- Investigate an incident and recommend next steps.

The investigation agent combines monitoring evidence with approved
runbook guidance. It is read-only and must never execute an action.

monitoring:
Use for operational investigation of pipeline failures, incidents,
execution history, and SLA breaches.

sql:
Use for analytical questions involving counts, statistics, failure
rates, trends, or aggregated pipeline execution data.

rag:
Use for troubleshooting guidance, investigation procedures,
root-cause possibilities, remediation recommendations, validation,
and escalation guidance from operational runbooks.

action:
Use when the user explicitly requests a state-changing operational
action, such as rerunning a pipeline.

The action route may only create an approval request.
It must never directly execute a production change.


Routing rules:

- Choose investigation when the request requires BOTH incident-specific
  operational evidence and troubleshooting/remediation guidance.

- Do not choose investigation for a simple status or failure-history
  question; use monitoring.

- Do not choose investigation for general troubleshooting guidance
  without a specific observed incident; use rag.

- Investigation may recommend an action, but it must never route that
  recommendation automatically to action.

- Choose action only when the user explicitly requests that a
  state-changing operation be performed.

- Questions about a specific observed pipeline failure, incident,
  execution, status, or what happened should route to monitoring.

- Questions asking for general troubleshooting instructions,
  remediation guidance, or how to fix a type of problem should
  route to rag.


Additional routing rules:

1. RAG

Route requests about documented procedures, runbooks,
troubleshooting instructions, recovery guides, and general
remediation knowledge to rag.

Example:
"What is the documented procedure for handling pipeline failures?"
-> rag


2. INVESTIGATION

Route questions asking whether an operational action is necessary,
advisable, or appropriate to investigation when the decision
depends on incident-specific evidence.

Example:
"Should I rerun customer_ingestion?"
-> investigation


3. ACTION

Route to action only when the user explicitly instructs the
system to request or perform a state-changing operation.

Examples:
"Rerun customer_ingestion."
-> action

"Request a rerun of customer_ingestion."
-> action

Questions, recommendations, and hypothetical discussions
are NOT action requests.


4. SAFETY

When uncertain whether a request is asking for advice or
authorizing an action, do not choose action.

Choose the appropriate read-only agent instead.

Never interpret an investigation recommendation as
permission to create an approval request.


Examples:

"Why did customer_ingestion fail?"
-> monitoring

"What happened to customer_ingestion?"
-> monitoring

"Show me the failed customer_ingestion run."
-> monitoring

"How should I troubleshoot schema drift?"
-> rag

"How do I fix Spark out-of-memory errors?"
-> rag

"What does the runbook recommend for API timeouts?"
-> rag

"What is the failure rate for customer_ingestion?"
-> sql

"Rerun customer_ingestion."
-> action

"Why did customer_ingestion fail and what should I do?"
-> investigation

"Investigate the customer_ingestion failure and tell me how to fix it."
-> investigation

"Should I rerun customer_ingestion?"
-> investigation
"""

    def route(
        self,
        user_query: str,
    ) -> SupervisorDecision:
        """
        Route to a specialist agent with an additional
        safety check for ambiguous action requests.
        """

        logger.info(
            "Supervisor received request for routing | query=%s",
            user_query,
        )

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_query),
        ]

        decision = self.router_llm.invoke(messages)

        # Prevent advice requests from becoming operational actions.
        if (
            decision.agent == "action"
            and is_advice_request(user_query)
        ):
            logger.warning(
                "Action route overridden for advice request | "
                "original_agent=%s",
                decision.agent,
            )

            return SupervisorDecision(
                agent="investigation",
                reason=(
                    "The user is asking whether an operational "
                    "action is appropriate, not authorizing it."
                ),
            )

        return decision

    def invoke(
        self,
        user_query: str,
        current_user: UserIdentity | None = None,
    ) -> str | dict:
        """
        Route the request and invoke the selected specialist agent.

        Read-only specialist agents remain available to
        authenticated users.

        State-changing action requests require REQUEST_ACTION
        permission.

        The Supervisor never performs operational actions directly.
        """

        decision = self.route(user_query)

        username = (
            current_user.username
            if current_user is not None
            else "agentops_copilot"
        )

        logger.info(
            "Supervisor routed request | "
            "agent=%s | reason=%s | user=%s",
            decision.agent,
            decision.reason,
            username,
        )

        if decision.agent == "monitoring":
            return self.monitoring_agent.invoke(user_query)

        if decision.agent == "sql":
            return self.sql_agent.invoke(user_query)

        if decision.agent == "rag":
            return self.rag_agent.invoke(user_query)

        if decision.agent == "investigation":
            logger.info(
                "Supervisor routing request to Investigation Agent."
            )

            return self.investigation_agent.invoke(user_query)

        if decision.agent == "action":
            if current_user is None:
                raise PermissionError(
                    "Authenticated identity is required "
                    "for operational action requests."
                )

            if not has_permission(
                current_user.roles,
                Permission.REQUEST_ACTION,
            ):
                raise PermissionError(
                    "REQUEST_ACTION permission is required."
                )

            logger.info(
                "Supervisor authorized action request | user=%s",
                current_user.username,
            )

            return self.action_agent.invoke(
                user_query,
                requested_by=current_user.username,
            )

        # Fail closed if routing behavior ever becomes invalid.
        raise ValueError(
            f"Unsupported supervisor agent: {decision.agent}"
        )