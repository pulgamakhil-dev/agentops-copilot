from app.core.config import get_settings
from app.executors.airflow import AirflowActionExecutor
from app.executors.base import ActionExecutor
from app.executors.simulated import SimulatedActionExecutor
from app.clients.airflow_client import AirflowClient


def create_executor(
    provider: str,
) -> ActionExecutor:
    """
    Create an operational executor based on application configuration.

    Infrastructure-specific configuration stays inside the factory so
    agents and execution services remain provider-independent.
    """

    normalized_provider = provider.strip().lower()

    if normalized_provider == "simulated":
        return SimulatedActionExecutor()

    if normalized_provider == "airflow":
        settings = get_settings()

        client = AirflowClient(
            base_url=settings.airflow_base_url,
            username=settings.airflow_username,
            password=settings.airflow_password,
            timeout_seconds=settings.airflow_timeout_seconds,
            max_retries=settings.airflow_max_retries,
            retry_delay_seconds=settings.airflow_retry_delay_seconds,
        )

        return AirflowActionExecutor(
            client=client
        )

    # Unknown providers fail safely instead of silently falling back.
    raise ValueError(
        f"Unsupported executor provider: {provider}"
    )