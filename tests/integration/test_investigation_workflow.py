
from unittest.mock import patch

from langchain_core.messages import AIMessage

from app.agents.investigation_agent import InvestigationAgent


def test_investigation_combines_monitoring_and_runbooks():
    agent = InvestigationAgent()

    monitoring_evidence = (
        "customer_ingestion failed with API_TIMEOUT. "
        "Run ID: run-e2e-001."
    )

    runbook_evidence = [
        {
            "source": "api_timeout.md",
            "content": (
                "Check upstream availability, review timeout "
                "settings, and validate pipeline recovery."
            ),
        }
    ]

    final_report = (
        "Observed evidence: customer_ingestion failed with API_TIMEOUT. "
        "Likely cause: an upstream API timeout; not yet confirmed. "
        "Recommended next steps: investigate upstream availability "
        "and follow the documented API timeout runbook."
    )

    with (
        patch.object(
            agent.monitoring_agent,
            "invoke",
            return_value=monitoring_evidence,
        ) as mock_monitoring,
        patch(
            "app.agents.investigation_agent.search_runbooks",
            return_value=runbook_evidence,
        ) as mock_search,
        patch.object(
            type(agent.llm),
            "invoke",
            autospec=True,
            return_value=AIMessage(content=final_report),
        ) as mock_llm,
    ):
        result = agent.invoke(
            "Investigate the customer_ingestion API timeout."
        )

    # Monitoring evidence was collected.
    mock_monitoring.assert_called_once()

    # FAISS retrieval was called directly.
    mock_search.assert_called_once()
    assert mock_search.call_args.kwargs["k"] == 5

    # The final LLM synthesis received both evidence sources.
    mock_llm.assert_called_once()
    messages = mock_llm.call_args.args[1]
    synthesis_prompt = messages[1].content

    assert monitoring_evidence in synthesis_prompt
    assert "api_timeout.md" in synthesis_prompt
    assert runbook_evidence[0]["content"] in synthesis_prompt

    # The investigation returned the final report.
    assert result == final_report