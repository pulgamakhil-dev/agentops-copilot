
from unittest.mock import patch
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

from app.agents.action_agent import (
    ActionAgent,
    PipelineRerunRequest,
)
from app.agents.investigation_agent import InvestigationAgent
from app.models.approval import ApprovalDecision
from app.executors.base import ExecutionResult
from app.services.approval_service import approval_service
from app.services.execution_service import execution_service


def test_investigation_to_approved_execution():
    pipeline = f"e2e_pipeline_{uuid4().hex[:8]}"
    requester = "e2e-operator"
    reviewer = "e2e-reviewer"
    executor = "e2e-executor"

    investigation = InvestigationAgent()
    action_agent = ActionAgent()

    evidence = (
        f"Pipeline {pipeline} failed with API_TIMEOUT. "
        "Upstream service availability is not yet confirmed."
    )

    guidance = (
        "Check upstream availability and timeout settings. "
        "Consider a controlled rerun after resolving the issue."
    )

    runbook_evidence = [
        {
            "source": "api_timeout.md",
            "content": guidance,
        }
    ]

    report = (
        f"Observed: {pipeline} failed with API_TIMEOUT. "
        "Recommended: investigate the upstream API, then "
        "consider requesting a controlled rerun."
    )

    # Phase 1: Read-only investigation.
    with (
        patch.object(
            investigation.monitoring_agent,
            "invoke",
            return_value=evidence,
        ) as mock_monitoring,
        patch(
            "app.agents.investigation_agent.search_runbooks",
            return_value=runbook_evidence,
        ) as mock_search,
        patch.object(
            type(investigation.llm),
            "invoke",
            autospec=True,
            return_value=AIMessage(content=report),
        ) as mock_llm,
        patch.object(
            execution_service.executor,
            "rerun_pipeline",
        ) as mock_executor,
    ):
        investigation_result = investigation.invoke(
            f"Investigate the failure of {pipeline}."
        )

        assert "API_TIMEOUT" in investigation_result
        assert "controlled rerun" in investigation_result

        mock_monitoring.assert_called_once()
        mock_search.assert_called_once()
        mock_llm.assert_called_once()

        retrieval_query = mock_search.call_args.kwargs["query"]
        assert evidence in retrieval_query
        assert mock_search.call_args.kwargs["k"] == 5

        synthesis_messages = mock_llm.call_args.args[1]
        synthesis_prompt = synthesis_messages[1].content

        assert evidence in synthesis_prompt
        assert guidance in synthesis_prompt
        assert "api_timeout.md" in synthesis_prompt

        mock_executor.assert_not_called()

    # Phase 2: A separate, explicit user request.
    with patch.object(
        action_agent,
        "parse_request",
        return_value=PipelineRerunRequest(
            pipeline_name=pipeline,
            reason=(
                "Request rerun following API timeout investigation."
            ),
        ),
    ) as mock_parser:
        approval_result = action_agent.invoke(
            f"Please request a rerun of {pipeline}.",
            requested_by=requester,
        )

    mock_parser.assert_called_once()

    assert approval_result["pipeline_name"] == pipeline
    assert approval_result["action"] == "rerun_pipeline"
    assert approval_result["status"] == "pending"
    assert approval_result["requested_by"] == requester

    approval_id = approval_result["approval_id"]

    # Phase 3: Execution must be blocked before approval.
    with patch.object(
        execution_service.executor,
        "rerun_pipeline",
    ) as mock_executor:
        with pytest.raises(PermissionError):
            execution_service.execute_approved_action(
                approval_id=approval_id,
                executed_by=executor,
            )

        mock_executor.assert_not_called()

    # Phase 4: A separate reviewer approves the request.
    decision = approval_service.decide(
        ApprovalDecision(
            approval_id=approval_id,
            approved=True,
            reviewer=reviewer,
            comment="Approved after investigation.",
        )
    )

    assert decision.status.value == "approved"

    # Phase 5: Authorized execution; external rerun is mocked.
    provider_result = ExecutionResult(
        success=True,
        execution_id="mock-provider-run-001",
        action_name="rerun_pipeline",
        resource_name=pipeline,
        status="completed",
        message="Mocked pipeline rerun completed.",
        metadata={"mocked": True},
    )

    with patch.object(
        execution_service.executor,
        "rerun_pipeline",
        return_value=provider_result,
    ) as mock_executor:
        result = execution_service.execute_approved_action(
            approval_id=approval_id,
            executed_by=executor,
        )

        mock_executor.assert_called_once_with(pipeline)

    assert result.success is True
    assert result.status == "completed"
    assert (
        result.metadata["provider_execution_id"]
        == "mock-provider-run-001"
    )