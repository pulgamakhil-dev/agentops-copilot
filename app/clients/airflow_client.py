import time
from typing import Any

import httpx

from app.core.logging import get_logger


logger = get_logger(__name__)


class AirflowClient:
    """
    HTTP client for the Apache Airflow REST API.

    Networking concerns such as authentication, timeouts, retries,
    and HTTP error handling are isolated from the execution layer.
    """

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        if not base_url.strip():
            raise ValueError("Airflow base URL cannot be empty.")

        if timeout_seconds <= 0:
            raise ValueError("Timeout must be greater than zero.")

        if max_retries < 0:
            raise ValueError("Maximum retries cannot be negative.")

        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

        auth = None

        # Basic authentication is configured only when credentials
        # have been supplied by the environment.
        if username and password:
            auth = httpx.BasicAuth(
                username=username,
                password=password,
            )

        self.client = httpx.Client(
            base_url=self.base_url,
            auth=auth,
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    def trigger_dag(
        self,
        dag_id: str,
        conf: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Trigger an Airflow DAG through the REST API.

        Transient connection/server failures are retried. Client-side
        errors fail immediately because retrying them usually will not
        correct an invalid request.
        """

        if not dag_id.strip():
            raise ValueError("Airflow DAG ID cannot be empty.")

        endpoint = f"/api/v1/dags/{dag_id}/dagRuns"

        payload = {
            "conf": conf or {},
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.post(
                    endpoint,
                    json=payload,
                )

                response.raise_for_status()

                logger.info(
                    "Airflow DAG trigger accepted | dag_id=%s",
                    dag_id,
                )

                return response.json()

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code

                # 4xx errors are normally configuration/request problems
                # and should not be retried automatically.
                if 400 <= status_code < 500:
                    logger.error(
                        "Airflow request rejected | "
                        "dag_id=%s | status=%s",
                        dag_id,
                        status_code,
                    )
                    raise

                if attempt >= self.max_retries:
                    raise

            except httpx.RequestError:
                if attempt >= self.max_retries:
                    raise

            logger.warning(
                "Retrying Airflow request | dag_id=%s | attempt=%s",
                dag_id,
                attempt + 1,
            )

            time.sleep(self.retry_delay_seconds)

        raise RuntimeError(
            "Airflow request failed unexpectedly."
        )

    def close(self) -> None:
        """
        Close the underlying HTTP connection pool.
        """

        self.client.close()