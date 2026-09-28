
from unittest.mock import patch

from langchain_core.messages import AIMessage

from app.agents.investigation_agent import InvestigationAgent


def test_investigation_never_requests_or_executes_actions():
    agent = InvestigationAgent()

    runbook_evidence = [
        {
            "source": "api_timeout.md",
            "content": "Check upstream API availability.",
        }
    ]

    with (
        patch.object(
            agent.monitoring_agent,
            "invoke",
            return_value="Pipeline failed with API_TIMEOUT.",
        ) as mock_monitoring,
        patch(
            "app.agents.investigation_agent.search_runbooks",
            return_value=runbook_evidence,
        ) as mock_search,
        patch.object(
            type(agent.llm),
            "invoke",
            autospec=True,
            return_value=AIMessage(
                content=(
                    "Investigate the API timeout before rerunning."
                )
            ),
        ) as mock_llm,
        patch(
            "app.services.action_service.action_service.request_action"
        ) as mock_request,
        patch(
            "app.services.execution_service.execution_service."
            "execute_approved_action"
        ) as mock_execute,
    ):
        result = agent.invoke(
            "Investigate the failed pipeline and recommend next steps."
        )

    assert "Investigate" in result

    mock_monitoring.assert_called_once()
    mock_search.assert_called_once()
    mock_llm.assert_called_once()

    mock_request.assert_not_called()
    mock_execute.assert_not_called()