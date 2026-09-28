
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.agents.monitoring_agent import MonitoringAgent
from app.core.config import get_settings
from app.core.logging import get_logger
from app.tools.rag_tools import search_runbooks


logger = get_logger(__name__)


class InvestigationAgent:
    """
    Coordinates evidence-based incident investigation.

    Combines:
    - Observed operational evidence from the Monitoring Agent
    - Approved runbook evidence retrieved directly from FAISS
    - An LLM-generated incident diagnosis

    This agent is read-only. It never creates approval requests
    or executes operational actions.
    """

    def __init__(self) -> None:
        settings = get_settings()

        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            temperature=0,
        )

        self.monitoring_agent = MonitoringAgent()

        self.system_prompt = """
You are the Investigation Agent for AgentOps Copilot.

Your responsibility is to synthesize operational evidence and
approved runbook guidance into a concise incident diagnosis.

You will receive:
1. The user's original question.
2. Monitoring evidence gathered from operational data.
3. Runbook passages retrieved from the knowledge base.

RULES:
- Treat monitoring results as observed operational evidence.
- Treat runbook passages as documented troubleshooting guidance.
- Do not invent failures, causes, metrics, or remediation steps.
- Clearly distinguish observed evidence from likely causes.
- Do not claim a root cause is confirmed unless evidence supports it.
- If evidence is insufficient, explicitly say so.
- Identify the runbook source supporting each recommendation.
- Do not describe general guidance as pipeline-specific unless
  the retrieved documentation explicitly names that pipeline.
- You may recommend an operational action when supported by evidence.
- Never execute an action.
- Never create an approval request.
- State-changing actions require a separate explicit user request
  and appropriate authorization.
- Keep the response concise and operationally useful.

STRUCTURE:
1. Observed evidence
2. Likely cause or current diagnosis
3. Relevant runbook guidance and sources
4. Recommended next steps
"""

    def invoke(self, user_query: str) -> str:
        """
        Run the read-only incident investigation workflow.
        """

        if not isinstance(user_query, str):
            raise TypeError(
                "Investigation query must be a string."
            )

        user_query = user_query.strip()

        if not user_query:
            raise ValueError(
                "Investigation query cannot be empty."
            )

        logger.info(
            "Investigation Agent started | query=%s",
            user_query,
        )

        # Phase 1: Collect operational evidence.
        monitoring_result = self.monitoring_agent.invoke(
            user_query
        )

        logger.info(
            "Investigation Agent monitoring phase completed."
        )

        # Phase 2: Retrieve runbook evidence directly from FAISS.
        # This avoids an additional LLM-driven tool-calling loop.
        rag_query = (
            "Find troubleshooting and remediation guidance "
            "relevant to the following incident.\n\n"
            f"Original request:\n{user_query}\n\n"
            f"Observed monitoring evidence:\n{monitoring_result}"
        )

        rag_evidence = search_runbooks(
            query=rag_query,
            k=5,
        )

        if rag_evidence:
            rag_result = "\n\n".join(
                (
                    f"Source: "
                    f"{item.get('source', 'unknown')}\n"
                    f"Content: {item.get('content', '')}"
                )
                for item in rag_evidence
            )
        else:
            rag_result = (
                "No relevant runbook evidence was retrieved."
            )

        logger.info(
            "Investigation Agent runbook phase completed | "
            "passages=%s",
            len(rag_evidence),
        )

        # Phase 3: Synthesize the incident investigation.
        synthesis_prompt = f"""
Original user request:
{user_query}

Observed monitoring evidence:
{monitoring_result}

Retrieved runbook evidence:
{rag_result}

Produce the final incident investigation response.

Use only the evidence provided above.
Distinguish confirmed observations from possible causes.
Cite relevant runbook source filenames when available.
Do not execute actions or create approval requests.
"""

        response = self.llm.invoke(
            [
                SystemMessage(
                    content=self.system_prompt
                ),
                HumanMessage(
                    content=synthesis_prompt
                ),
            ]
        )

        logger.info(
            "Investigation Agent completed."
        )

        return response.content