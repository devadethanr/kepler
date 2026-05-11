"""Approval sub-repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ApprovalRow, EntryIntentRow, OrderIntentRow, PendingApproval
from .. import models as models_module
from .entry_intents import EntryIntentRepository


IST = ZoneInfo("Asia/Kolkata")
VISIBLE_APPROVAL_STATUSES = {"pending", "approved", "queued"}
ACTIVE_APPROVAL_ORDER_STATUSES = {"awaiting_approval", "approved", "queued"}


def _as_ist(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)


def _approval_status(
    *,
    approved: bool | None,
    execution_requested: bool,
    order_intent_status: str | None = None,
    explicit_status: str | None = None,
) -> str:
    if explicit_status:
        normalized = explicit_status.strip().lower()
        if normalized:
            return normalized
    if order_intent_status:
        normalized = order_intent_status.strip().lower()
        if normalized and normalized not in ACTIVE_APPROVAL_ORDER_STATUSES:
            return normalized
    if approved is False:
        return "rejected"
    if approved is True and execution_requested:
        return "queued"
    if approved is True:
        return "approved"
    return "pending"


def _entry_intent_status(
    *,
    approved: bool | None,
    execution_requested: bool,
    order_intent_status: str | None = None,
) -> str:
    if order_intent_status:
        normalized = order_intent_status.strip().lower()
        if normalized and normalized not in {"awaiting_approval"}:
            return normalized
    if approved is False:
        return "cancelled"
    if approved is True and execution_requested:
        return "queued"
    if approved is True:
        return "approved"
    return "awaiting_approval"


class ApprovalRepository:
    """Approval and intent lifecycle management."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def approvals_exist(self) -> bool:
        return self.session.scalar(select(ApprovalRow.approval_id).limit(1)) is not None

    def get_pending_approvals_payload(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(ApprovalRow)
            .where(ApprovalRow.status.in_(sorted(VISIBLE_APPROVAL_STATUSES)))
            .order_by(ApprovalRow.created_at_effective.asc(), ApprovalRow.approval_id.asc())
        ).all()
        now = datetime.now(IST)
        active: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row.payload)
            try:
                approval = PendingApproval.model_validate(payload)
            except Exception:
                continue
            if _as_ist(approval.expires_at) <= now:
                continue
            active.append(payload)
        return active

    def get_execution_requested_approvals(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(ApprovalRow)
            .where(
                ApprovalRow.execution_requested.is_(True),
                ApprovalRow.status.in_(("approved", "queued")),
            )
            .order_by(ApprovalRow.created_at_effective.asc(), ApprovalRow.approval_id.asc())
        ).all()
        return [dict(row.payload) for row in rows]

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        row = self.session.get(ApprovalRow, approval_id)
        if row is None:
            return None
        return dict(row.payload)

    def update_approval_payload(
        self,
        approval_id: str,
        payload: dict[str, Any],
        *,
        source: str,
    ) -> dict[str, Any] | None:
        from .order_intents import OrderIntentRepository
        from .events import EventRepository

        row = self.session.get(ApprovalRow, approval_id)
        if row is None:
            return None

        current = dict(row.payload or {})
        merged = {**current, **dict(payload)}
        approval = PendingApproval.model_validate(merged)
        normalized = approval.model_dump(mode="json")
        approved = normalized.get("approved")
        execution_requested = bool(normalized.get("execution_requested", False))
        order_intent = (
            OrderIntentRepository(self.session).get_order_intent(str(normalized["order_intent_id"]))
            if normalized.get("order_intent_id")
            else None
        )
        order_intent_status = (
            str(order_intent["status"]) if order_intent is not None else "awaiting_approval"
        )
        if approved is True and execution_requested:
            order_intent_status = "queued"
        elif approved is True:
            order_intent_status = "approved"
        elif approved is False:
            order_intent_status = "cancelled"

        row.ticker = approval.ticker
        row.entry_intent_id = str(normalized["entry_intent_id"])
        row.order_intent_id = str(normalized["order_intent_id"])
        row.status = _approval_status(
            approved=approved,
            execution_requested=execution_requested,
            order_intent_status=order_intent_status,
            explicit_status=normalized.get("status"),
        )
        row.approved = approved
        row.execution_requested = execution_requested
        row.execution_request_id = normalized.get("execution_request_id")
        row.created_at_effective = approval.created_at
        row.expires_at = approval.expires_at
        normalized["status"] = row.status
        row.payload = normalized

        EntryIntentRepository(self.session).upsert_entry_intent(
            entry_intent_id=str(normalized["entry_intent_id"]),
            ticker=approval.ticker,
            status=_entry_intent_status(
                approved=approved,
                execution_requested=execution_requested,
                order_intent_status=order_intent_status,
            ),
            approval_id=approval_id,
            order_intent_id=str(normalized["order_intent_id"]),
            payload=normalized,
            source=source,
        )
        OrderIntentRepository(self.session).upsert_order_intent(
            order_intent_id=str(normalized["order_intent_id"]),
            ticker=approval.ticker,
            status=order_intent_status,
            approval_id=approval_id,
            entry_intent_id=str(normalized["entry_intent_id"]),
            broker_order_id=(
                str(normalized.get("broker_order_id"))
                if normalized.get("broker_order_id") not in (None, "")
                else None
            ),
            broker_tag=(
                str(normalized.get("broker_tag"))
                if normalized.get("broker_tag") not in (None, "")
                else None
            ),
            payload=normalized,
            source=source,
        )
        EventRepository(self.session).append_execution_event(
            event_type="approval_updated",
            entity_type="approval",
            entity_id=approval_id,
            source=source,
            payload={"ticker": approval.ticker, "status": row.status},
        )
        return normalized

    def replace_pending_approvals(
        self,
        payload: list[dict[str, Any]],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        from .order_intents import OrderIntentRepository
        from .events import EventRepository

        existing = {
            str(row.approval_id): row
            for row in self.session.scalars(select(ApprovalRow)).all()
        }
        seen_approval_ids: set[str] = set()
        normalized_payload: list[dict[str, Any]] = []

        for item in payload:
            incoming = dict(item)
            approval = PendingApproval.model_validate(item)
            normalized = approval.model_dump(mode="json")
            approval_id = str(normalized["approval_id"])
            entry_intent_id = str(normalized["entry_intent_id"])
            order_intent_id = str(normalized["order_intent_id"])
            row = existing.get(approval_id)
            if row is None:
                row = ApprovalRow(approval_id=approval_id, ticker=approval.ticker)
                existing[approval_id] = row
                self.session.add(row)

            approved_provided = "approved" in incoming
            execution_requested_provided = "execution_requested" in incoming
            request_id_provided = "execution_request_id" in incoming
            broker_tag_provided = "broker_tag" in incoming
            existing_payload = dict(row.payload or {})

            approved = (
                normalized.get("approved") if approved_provided else row.approved
            )
            execution_requested = (
                bool(normalized.get("execution_requested", False))
                if execution_requested_provided
                else bool(row.execution_requested)
            )
            execution_request_id = (
                str(normalized["execution_request_id"])
                if request_id_provided and normalized.get("execution_request_id") is not None
                else None
                if request_id_provided
                else row.execution_request_id
            )
            broker_tag = (
                str(normalized.get("broker_tag"))
                if broker_tag_provided and normalized.get("broker_tag") not in (None, "")
                else None
                if broker_tag_provided
                else str(existing_payload.get("broker_tag"))
                if existing_payload.get("broker_tag") not in (None, "")
                else None
            )

            normalized["approved"] = approved
            normalized["execution_requested"] = execution_requested
            normalized["execution_request_id"] = execution_request_id
            normalized["approval_id"] = approval_id
            normalized["entry_intent_id"] = entry_intent_id
            normalized["order_intent_id"] = order_intent_id
            if broker_tag is not None:
                normalized["broker_tag"] = broker_tag

            order_intent_status = "awaiting_approval"
            if approved is True and execution_requested:
                order_intent_status = "queued"
            elif approved is True:
                order_intent_status = "approved"
            elif approved is False:
                order_intent_status = "cancelled"

            row.ticker = approval.ticker
            row.entry_intent_id = entry_intent_id
            row.order_intent_id = order_intent_id
            row.status = _approval_status(
                approved=approved,
                execution_requested=execution_requested,
                order_intent_status=order_intent_status,
                explicit_status=normalized.get("status"),
            )
            row.approved = approved
            row.execution_requested = execution_requested
            row.execution_request_id = execution_request_id
            row.created_at_effective = approval.created_at
            row.expires_at = approval.expires_at
            normalized["status"] = row.status
            row.payload = normalized

            EntryIntentRepository(self.session).upsert_entry_intent(
                entry_intent_id=entry_intent_id,
                ticker=approval.ticker,
                status=_entry_intent_status(
                    approved=approved,
                    execution_requested=execution_requested,
                    order_intent_status=order_intent_status,
                ),
                approval_id=approval_id,
                order_intent_id=order_intent_id,
                payload=normalized,
                source=source,
            )
            OrderIntentRepository(self.session).upsert_order_intent(
                order_intent_id=order_intent_id,
                ticker=approval.ticker,
                status=order_intent_status,
                approval_id=approval_id,
                entry_intent_id=entry_intent_id,
                broker_order_id=(
                    str(normalized.get("broker_order_id"))
                    if normalized.get("broker_order_id") not in (None, "")
                    else None
                ),
                broker_tag=broker_tag,
                payload=normalized,
                source=source,
            )

            normalized_payload.append(normalized)
            seen_approval_ids.add(approval_id)

        for approval_id, row in existing.items():
            if approval_id in seen_approval_ids:
                continue
            if row.status in {"pending", "approved"} and not row.execution_requested:
                row.status = "superseded"
                row.execution_requested = False
                row.execution_request_id = None
                next_payload = dict(row.payload)
                next_payload["status"] = "superseded"
                next_payload["execution_requested"] = False
                next_payload["execution_request_id"] = None
                row.payload = next_payload
                continue
            order_intent = (
                OrderIntentRepository(self.session).get_order_intent(str(row.order_intent_id))
                if row.order_intent_id
                else None
            )
            next_status = _approval_status(
                approved=row.approved,
                execution_requested=False,
                order_intent_status=(
                    str(order_intent["status"])
                    if order_intent is not None
                    else None
                ),
            )
            row.status = next_status
            row.execution_requested = False
            row.execution_request_id = None
            next_payload = dict(row.payload)
            next_payload["status"] = next_status
            next_payload["execution_requested"] = False
            next_payload["execution_request_id"] = None
            row.payload = next_payload

        EventRepository(self.session).append_execution_event(
            event_type="approvals_replaced",
            entity_type="approvals",
            entity_id="pending",
            source=source,
            payload={"count": len(normalized_payload)},
        )
        return self.get_pending_approvals_payload()