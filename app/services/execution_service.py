from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import SessionLocal
from app.db.models import ExecutionRecord
from app.executors.base import ActionExecutor, ExecutionResult
from app.executors.factory import create_executor
from app.models.approval import ApprovalStatus
from app.services.approval_service import approval_service
from app.services.audit_service import audit_service


logger = get_logger(__name__)


class ExecutionService:
    """
    Executes approved operational actions through a configured executor.

    The service reserves an execution record before contacting the
    executor. This provides database-backed idempotency and prevents
    the same approval from being executed concurrently.
    """

    def __init__(
        self,
        executor: ActionExecutor | None = None,
    ) -> None:
        settings = get_settings()

        self.executor_provider = (
            settings.executor_provider.strip().lower()
        )

        # Dependency injection allows tests to provide a safe executor,
        # while runtime uses the configured execution provider.
        self.executor = executor or create_executor(
            self.executor_provider
        )

    def execute_approved_action(
        self,
        approval_id: str,
        executed_by: str | None = None,
    ) -> ExecutionResult:
        """
        Execute an approved operational action exactly once.

        executed_by identifies the authenticated actor who initiated
        the execution. It is persisted as part of the audit trail.
        """

        approval = approval_service.get_request(
            approval_id
        )

        if approval.status != ApprovalStatus.APPROVED:
            raise PermissionError(
                "Action cannot be executed because the approval "
                f"status is '{approval.status.value}'."
            )

        if not approval.resource_type:
            raise ValueError(
                "Resource type is missing from approval record."
            )

        if not approval.resource_name:
            raise ValueError(
                "Resource name is missing from approval record."
            )

        # AgentOps owns this canonical execution ID.
        execution_id = str(uuid4())

        # Reserve execution before contacting the provider.
        self._reserve_execution(
            execution_id=execution_id,
            approval_id=approval.approval_id,
            action_name=approval.action_name,
            resource_type=approval.resource_type,
            resource_name=approval.resource_name,
            executed_by=executed_by,
        )

        logger.info(
            "Execution reserved | "
            "execution_id=%s | approval_id=%s | "
            "executor=%s | executed_by=%s",
            execution_id,
            approval.approval_id,
            self.executor_provider,
            executed_by,
        )

        try:
            provider_result = self._execute_action(
                action_name=approval.action_name,
                resource_type=approval.resource_type,
                resource_name=approval.resource_name,
            )

            self._mark_execution_completed(
                execution_id=execution_id,
                result=provider_result,
            )

            logger.info(
                "Execution completed | "
                "execution_id=%s | approval_id=%s | "
                "status=%s | executed_by=%s",
                execution_id,
                approval.approval_id,
                provider_result.status,
                executed_by,
            )

            # Return the AgentOps execution ID as the canonical ID.
            # The executor-generated ID is preserved as provider metadata.
            metadata = dict(provider_result.metadata or {})

            metadata["provider_execution_id"] = (
                provider_result.execution_id
            )

            return ExecutionResult(
                success=provider_result.success,
                execution_id=execution_id,
                action_name=provider_result.action_name,
                resource_name=provider_result.resource_name,
                status=provider_result.status,
                message=provider_result.message,
                metadata=metadata,
            )

        except Exception as exc:
            self._mark_execution_failed(
                execution_id=execution_id,
                error_message=str(exc),
            )

            logger.exception(
                "Execution failed | "
                "execution_id=%s | approval_id=%s | "
                "executed_by=%s",
                execution_id,
                approval.approval_id,
                executed_by,
            )

            raise

    def _reserve_execution(
        self,
        execution_id: str,
        approval_id: str,
        action_name: str,
        resource_type: str,
        resource_name: str,
        executed_by: str | None = None,
    ) -> None:
        """
        Atomically reserve an execution for an approval.

        The unique approval_id constraint prevents another request
        from reserving the same approved action.
        """

        session: Session = SessionLocal()

        try:
            record = ExecutionRecord(
                execution_id=execution_id,
                approval_id=approval_id,
                action_name=action_name,
                resource_type=resource_type,
                resource_name=resource_name,
                executor_provider=self.executor_provider,
                executed_by=executed_by,
                status="started",
                message="Execution reserved.",
                created_at=datetime.now(timezone.utc),
                completed_at=None,
            )

            session.add(record)
            session.flush()

            audit_service.record_event(
                event_type="EXECUTION_STARTED",
                actor=executed_by or "agentops_copilot",
                action_name=action_name,
                resource_type=resource_type,
                resource_name=resource_name,
                approval_id=approval_id,
                execution_id=execution_id,
                outcome="started",
                message="Execution reserved.",
                session=session,
            )

            session.commit()

        except IntegrityError as exc:
            session.rollback()

            logger.warning(
                "Duplicate execution prevented | approval_id=%s",
                approval_id,
            )

            raise ValueError(
                "This approval has already been submitted "
                "for execution."
            ) from exc

        finally:
            session.close()

    def _execute_action(
        self,
        action_name: str,
        resource_type: str,
        resource_name: str,
    ) -> ExecutionResult:
        """
        Dispatch only explicitly supported operational actions.
        """

        if action_name == "rerun_pipeline":
            if resource_type != "pipeline":
                raise ValueError(
                    "Invalid resource type for pipeline rerun."
                )

            return self.executor.rerun_pipeline(
                resource_name
            )

        raise ValueError(
            f"Unsupported action: {action_name}"
        )

    def _mark_execution_completed(
        self,
        execution_id: str,
        result: ExecutionResult,
    ) -> None:
        """
        Persist the successful provider result.
        """

        session: Session = SessionLocal()

        try:
            record = session.get(
                ExecutionRecord,
                execution_id,
            )

            if record is None:
                raise RuntimeError(
                    "Reserved execution record was not found."
                )

            record.status = result.status
            record.message = result.message
            record.completed_at = datetime.now(timezone.utc)


            audit_service.record_event(
                event_type="EXECUTION_COMPLETED",
                actor=record.executed_by or "agentops_copilot",
                action_name=record.action_name,
                resource_type=record.resource_type,
                resource_name=record.resource_name,
                approval_id=record.approval_id,
                execution_id=record.execution_id,
                outcome=result.status,
                message=result.message,
                session=session,
        )

            session.commit()

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    def _mark_execution_failed(
        self,
        execution_id: str,
        error_message: str,
    ) -> None:
        """
        Persist execution failure while keeping the reservation.

        Keeping the failed record prevents an uncontrolled retry
        from triggering the same approved action again.
        """

        session: Session = SessionLocal()

        try:
            record = session.get(
                ExecutionRecord,
                execution_id,
            )

            if record is None:
                logger.error(
                    "Execution failure could not be recorded | "
                    "execution_id=%s",
                    execution_id,
                )
                return

            record.status = "failed"
            record.message = error_message
            record.completed_at = datetime.now(timezone.utc)

            audit_service.record_event(
                event_type="EXECUTION_FAILED",
                actor=record.executed_by or "agentops_copilot",
                action_name=record.action_name,
                resource_type=record.resource_type,
                resource_name=record.resource_name,
                approval_id=record.approval_id,
                execution_id=record.execution_id,
                outcome="failed",
                message=error_message,
                session=session,
            )

            session.commit()

        except Exception:
            session.rollback()

            logger.exception(
                "Unable to persist execution failure | "
                "execution_id=%s",
                execution_id,
            )

        finally:
            session.close()


# Shared execution service used by the API.
execution_service = ExecutionService()