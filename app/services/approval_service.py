from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session
from app.services.audit_service import audit_service
from app.core.guardrails import ActionRisk, classify_action
from app.core.logging import get_logger
from app.db.database import SessionLocal
from app.db.models import ApprovalRecord
from app.models.approval import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
)


logger = get_logger(__name__)


class ApprovalService:
    """
    Manages persistent approval requests for controlled actions.

    Approval decisions are stored in the database so they remain
    available across application restarts.
    """

    @staticmethod
    def _to_response(record: ApprovalRecord) -> ApprovalRequest:
        """
        Convert the database record into the API/domain model.
        """

        return ApprovalRequest(
            approval_id=record.approval_id,
            action_name=record.action_name,
            action_risk=ActionRisk(record.action_risk),
            resource_type=record.resource_type,
            resource_name=record.resource_name,
            reason=record.reason,
            requested_by=record.requested_by,
            status=ApprovalStatus(record.status),
            created_at=record.created_at,
            reviewer=record.reviewer,
            comment=record.comment,
            decided_at=record.decided_at,
        )

    def create_request(
        self,
        action_name: str,
        reason: str,
        resource_type: str | None = None,
        resource_name: str | None = None,
        requested_by: str = "agentops_copilot",
    ) -> ApprovalRequest:
        """
        Create and persist an approval request.

        requested_by identifies the actor or system that initiated
        the request. The default preserves compatibility with
        internal agent-generated requests.

        Read-only actions should not enter the approval workflow.
        Blocked actions are recorded for audit purposes but cannot
        later be approved.
        """

        risk = classify_action(action_name)

        if risk == ActionRisk.READ_ONLY:
            raise ValueError(
                "Read-only actions do not require approval."
            )

        status = (
            ApprovalStatus.BLOCKED
            if risk == ActionRisk.BLOCKED
            else ApprovalStatus.PENDING
        )

        record = ApprovalRecord(
            approval_id=str(uuid4()),
            action_name=action_name,
            action_risk=risk.value,
            resource_type=resource_type,
            resource_name=resource_name,
            reason=reason,
            requested_by=requested_by,
            status=status.value,
            created_at=datetime.now(timezone.utc),
        )

        session: Session = SessionLocal()

        try:
            session.add(record)
            session.flush()

            audit_service.record_event(
                event_type="ACTION_REQUESTED",
                actor=record.requested_by,
                action_name=record.action_name,
                resource_type=record.resource_type,
                resource_name=record.resource_name,
                approval_id=record.approval_id,
                outcome=record.status,
                message=record.reason,
                session=session,
            )

            session.commit()
            session.refresh(record)

            logger.info(
                "Approval request persisted | "
                "approval_id=%s | action=%s | status=%s | "
                "requested_by=%s",
                record.approval_id,
                record.action_name,
                record.status,
                record.requested_by,
            )

            return self._to_response(record)

        except Exception:
            session.rollback()

            logger.exception(
                "Failed to persist approval request | "
                "action=%s | requested_by=%s",
                action_name,
                requested_by,
            )

            raise

        finally:
            session.close()

    def get_request(
        self,
        approval_id: str,
    ) -> ApprovalRequest:
        """
        Retrieve an approval request from persistent storage.
        """

        session: Session = SessionLocal()

        try:
            record = session.get(
                ApprovalRecord,
                approval_id,
            )

            if record is None:
                raise KeyError(
                    f"Approval request not found: {approval_id}"
                )

            return self._to_response(record)

        finally:
            session.close()

    def decide(
        self,
        decision: ApprovalDecision,
    ) -> ApprovalRequest:
        """
        Persist a human approval or rejection decision.

        The requester cannot review their own request.
        Approval changes authorization state only and does not
        execute the requested operational action.
        """

        session: Session = SessionLocal()

        try:
            record = session.get(
                ApprovalRecord,
                decision.approval_id,
            )

            if record is None:
                raise KeyError(
                    "Approval request not found: "
                    f"{decision.approval_id}"
                )

            if record.status == ApprovalStatus.BLOCKED.value:
                raise ValueError(
                    "Blocked actions cannot be approved."
                )

            if record.status != ApprovalStatus.PENDING.value:
                raise ValueError(
                    "Approval request has already been decided."
                )

            # Enforce separation of duties.
            # The actor who requested the action cannot also
            # approve or reject that same request.
            if (
                record.requested_by
                and decision.reviewer
                and record.requested_by.strip().lower()
                == decision.reviewer.strip().lower()
            ):
                logger.warning(
                    "Self-approval blocked | "
                    "approval_id=%s | requester=%s | reviewer=%s",
                    record.approval_id,
                    record.requested_by,
                    decision.reviewer,
                )

                raise ValueError(
                    "Requester cannot review their own approval request."
                )

            record.status = (
                ApprovalStatus.APPROVED.value
                if decision.approved
                else ApprovalStatus.REJECTED.value
            )

            record.reviewer = decision.reviewer
            record.comment = decision.comment
            record.decided_at = datetime.now(timezone.utc)

            audit_service.record_event(
                event_type=(
                    "APPROVAL_GRANTED"
                    if decision.approved
                    else "APPROVAL_REJECTED"
                ),
                actor=decision.reviewer,
                action_name=record.action_name,
                resource_type=record.resource_type,
                resource_name=record.resource_name,
                approval_id=record.approval_id,
                outcome=record.status,
                message=decision.comment,
                session=session,
        )

            session.commit()
            session.refresh(record)

            logger.info(
                "Approval decision persisted | "
                "approval_id=%s | status=%s | "
                "requester=%s | reviewer=%s",
                record.approval_id,
                record.status,
                record.requested_by,
                record.reviewer,
            )

            return self._to_response(record)

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()


# Shared service instance used by the API and controlled-action tools.
approval_service = ApprovalService()