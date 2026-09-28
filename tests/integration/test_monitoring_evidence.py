
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.messages.tool import ToolMessage

from app.agents.monitoring_agent import MonitoringAgent


def test_monitoring_agent_uses_failed_run_evidence():
    agent = MonitoringAgent()

    fake_failure = {
        "run_id": "run-e2e-001",
        "pipeline_name": "customer_ingestion",
        "status": "failed",
        "error_code": "API_TIMEOUT",
        "error_category": "API_TIMEOUT",
        "duration_seconds": 420,
        "incident_id": "incident-e2e-001",
    }

    tool_request = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_failed_pipeline_runs",
                "args": {
                    "pipeline_name": "customer_ingestion",
                    "limit": 20,
                },
                "id": "test-tool-call-001",
                "type": "tool_call",
            }
        ],
    )

    final_answer = AIMessage(
        content=(
            "Monitoring found that customer_ingestion failed. "
            "Run run-e2e-001 reported API_TIMEOUT after 420 seconds."
        )
    )

    with (
        patch.object(
            type(agent.llm_with_tools),
            "invoke",
            autospec=True,
            side_effect=[
                tool_request,
                final_answer,
            ],
        ) as mock_llm,
        patch(
            "app.tools.monitoring_tools.get_failed_pipeline_runs",
            return_value=[fake_failure],
        ) as mock_tool,
    ):
        result = agent.invoke(
            "Investigate the failed customer_ingestion pipeline."
        )


    mock_tool.assert_called_once_with(
        limit=20,
        pipeline_name="customer_ingestion",
    )
    assert mock_llm.call_count == 2
    assert "customer_ingestion" in result
    assert "API_TIMEOUT" in result

    second_call_messages = mock_llm.call_args_list[1].args[1]

    assert any(
        isinstance(message, ToolMessage)
        and "API_TIMEOUT" in str(message.content)
        for message in second_call_messages
    )