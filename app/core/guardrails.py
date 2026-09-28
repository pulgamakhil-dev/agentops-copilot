from enum import Enum


class ActionRisk(str, Enum):
    """
    Risk classification for actions proposed by AgentOps Copilot.
    """

    READ_ONLY = "read_only"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"


# Actions that are safe for the agent to perform automatically.
READ_ONLY_ACTIONS = {
    "search_runbooks",
    "get_failed_pipeline_runs",
    "get_pipeline_history",
    "get_incident_history",
    "get_sla_breaches",
    "query_pipeline_metrics",
}

# Actions that may change production state.
# These must never execute without explicit human approval.
APPROVAL_REQUIRED_ACTIONS = {
    "rerun_pipeline",
    "restart_job",
    "change_pipeline_config",
    "change_timeout",
    "scale_compute",
}

# Actions the agent is never permitted to execute.
BLOCKED_ACTIONS = {
    "delete_pipeline",
    "drop_table",
    "delete_production_data",
    "disable_security_controls",
}


def classify_action(action_name: str) -> ActionRisk:
    """
    Determine the risk level of an AgentOps action.

    Unknown actions default to APPROVAL_REQUIRED rather than being
    automatically trusted. This provides a fail-safe default.
    """

    normalized_action = action_name.strip().lower()

    if normalized_action in READ_ONLY_ACTIONS:
        return ActionRisk.READ_ONLY

    if normalized_action in BLOCKED_ACTIONS:
        return ActionRisk.BLOCKED

    return ActionRisk.APPROVAL_REQUIRED