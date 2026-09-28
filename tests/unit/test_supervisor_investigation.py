from unittest.mock import patch

from app.agents.supervisor import (
    SupervisorAgent,
    SupervisorDecision,
)


@patch("app.agents.supervisor.InvestigationAgent")
@patch("app.agents.supervisor.RAGAgent")
@patch("app.agents.supervisor.SQLAgent")
@patch("app.agents.supervisor.MonitoringAgent")
@patch("app.agents.supervisor.ActionAgent")
@patch("app.agents.supervisor.ChatOllama")
def test_supervisor_routes_investigation_request(
    mock_chat_ollama,
    mock_action_agent,
    mock_monitoring_agent,
    mock_sql_agent,
    mock_rag_agent,
    mock_investigation_agent,
) -> None:
    investigation_instance = (
        mock_investigation_agent.return_value
    )

    investigation_instance.invoke.return_value = (
        "Investigation completed."
    )

    supervisor = SupervisorAgent()

    user_query = (
        "Why did customer_ingestion fail "
        "and what should I do?"
    )

    with patch.object(
        supervisor,
        "route",
        return_value=SupervisorDecision(
            agent="investigation",
            reason=(
                "The request requires incident evidence "
                "and remediation guidance."
            ),
        ),
    ):
        result = supervisor.invoke(
            user_query
        )

    investigation_instance.invoke.assert_called_once_with(
        user_query
    )

    mock_monitoring_agent.return_value.invoke.assert_not_called()
    mock_sql_agent.return_value.invoke.assert_not_called()
    mock_rag_agent.return_value.invoke.assert_not_called()
    mock_action_agent.return_value.invoke.assert_not_called()

    assert result == "Investigation completed."


@patch("app.agents.supervisor.InvestigationAgent")
@patch("app.agents.supervisor.RAGAgent")
@patch("app.agents.supervisor.SQLAgent")
@patch("app.agents.supervisor.MonitoringAgent")
@patch("app.agents.supervisor.ActionAgent")
@patch("app.agents.supervisor.ChatOllama")
def test_action_request_does_not_use_investigation_agent(
    mock_chat_ollama,
    mock_action_agent,
    mock_monitoring_agent,
    mock_sql_agent,
    mock_rag_agent,
    mock_investigation_agent,
) -> None:
    supervisor = SupervisorAgent()

    with patch.object(
        supervisor,
        "route",
        return_value=SupervisorDecision(
            agent="action",
            reason="User explicitly requested a pipeline rerun.",
        ),
    ):
        try:
            supervisor.invoke(
                "Rerun customer_ingestion."
            )
        except PermissionError:
            pass

    mock_investigation_agent.return_value.invoke.assert_not_called()
    mock_monitoring_agent.return_value.invoke.assert_not_called()
    mock_sql_agent.return_value.invoke.assert_not_called()
    mock_rag_agent.return_value.invoke.assert_not_called()
    mock_action_agent.return_value.invoke.assert_not_called()