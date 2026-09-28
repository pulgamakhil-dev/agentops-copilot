
from unittest.mock import patch

from langchain_core.messages import AIMessage

from app.agents.investigation_agent import InvestigationAgent


@patch("app.agents.investigation_agent.search_runbooks")
@patch("app.agents.investigation_agent.MonitoringAgent")
@patch("app.agents.investigation_agent.ChatOllama")
def test_investigation_agent_combines_monitoring_and_rag(
    mock_chat_ollama,
    mock_monitoring_agent,
    mock_search_runbooks,
) -> None:
    """
    Verify that the Investigation Agent gathers monitoring
    evidence, retrieves runbook passages directly, and
    synthesizes both into an incident report.
    """

    monitoring_evidence = (
        "customer_ingestion failed because the source "
        "schema changed unexpectedly."
    )

    runbook_guidance = (
        "The runbook recommends validating the source schema "
        "before rerunning the pipeline."
    )

    monitoring_instance = mock_monitoring_agent.return_value
    monitoring_instance.invoke.return_value = monitoring_evidence

    mock_search_runbooks.return_value = [
        {
            "source": "schema_drift.md",
            "content": runbook_guidance,
        }
    ]

    llm_instance = mock_chat_ollama.return_value
    llm_instance.invoke.return_value = AIMessage(
        content=(
            "The pipeline failed after a schema change. "
            "Validate the source schema before requesting a rerun."
        )
    )

    agent = InvestigationAgent()

    user_query = (
        "Why did customer_ingestion fail "
        "and what should I do?"
    )

    result = agent.invoke(user_query)

    # Monitoring receives the original user query.
    monitoring_instance.invoke.assert_called_once_with(
        user_query
    )

    # FAISS retrieval receives both the query and monitoring evidence.
    mock_search_runbooks.assert_called_once()

    retrieval_kwargs = mock_search_runbooks.call_args.kwargs
    retrieval_query = retrieval_kwargs["query"]

    assert user_query in retrieval_query
    assert monitoring_evidence in retrieval_query
    assert retrieval_kwargs["k"] == 5

    # Final synthesis includes both evidence sources.
    llm_instance.invoke.assert_called_once()

    synthesis_messages = llm_instance.invoke.call_args.args[0]
    synthesis_content = synthesis_messages[1].content

    assert user_query in synthesis_content
    assert monitoring_evidence in synthesis_content
    assert runbook_guidance in synthesis_content
    assert "schema_drift.md" in synthesis_content

    assert result == (
        "The pipeline failed after a schema change. "
        "Validate the source schema before requesting a rerun."
    )