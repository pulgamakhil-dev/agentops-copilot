from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    run_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    pipeline_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    business_domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    environment: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    source_system: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    target_system: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    orchestrator: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    job_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    attempt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    scheduled_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    records_read: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    records_written: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    records_rejected: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    data_quality_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    sla_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sla_breach_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    error_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    error_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    owner_team: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    region: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    correlation_id: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    incident_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    recovery_action: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )


class ApprovalRecord(Base):
    """
    Persistent audit record for controlled operational actions.

    Approval records are stored in the database so human decisions
    remain available across application restarts.
    """

    __tablename__ = "approval_requests"

    approval_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    action_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    action_risk: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    requested_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    reviewer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Type of operational resource targeted by the action.
    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    # Exact resource identifier used by the execution layer.
    resource_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )


class ExecutionRecord(Base):
    """
    Persistent audit record for controlled action executions.

    Each approval can produce at most one execution record, helping
    prevent accidental duplicate execution.
    """

    __tablename__ = "execution_records"

    execution_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    # Unique approval ID provides database-level protection
    # against duplicate execution.
    approval_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )

    action_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    resource_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    executor_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Authenticated user who initiated the execution.
    # This completes the audit trail from request to execution.
    executed_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

class AuditEvent(Base):
    """
    Immutable audit event for security-sensitive AgentOps activity.

    This table provides a unified timeline across approval and
    execution workflows without replacing their domain records.
    """

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    action_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    resource_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    resource_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    approval_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    execution_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    outcome: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )