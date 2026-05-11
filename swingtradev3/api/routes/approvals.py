from __future__ import annotations

from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException

from auth.kite.client import has_kite_session
from config import cfg, runtime_flags
from api.sse_broadcaster import broadcaster
from memory.db import session_scope
from memory.projections import project_all_managed_files
from memory.repositories import MemoryRepository
from models import ApprovalResponse, PendingApproval
from policy.effective_policy import new_entries_block_reason

router = APIRouter()
IST = ZoneInfo("Asia/Kolkata")


def _persist_order_intent(approval_payload: dict[str, object], *, status: str) -> None:
    order_intent_id = str(approval_payload.get("order_intent_id") or "").strip()
    approval_id = str(approval_payload.get("approval_id") or "").strip() or None
    entry_intent_id = str(approval_payload.get("entry_intent_id") or "").strip() or None
    ticker = str(approval_payload.get("ticker") or "").strip().upper()
    if not order_intent_id or not ticker:
        return
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status=status,
            approval_id=approval_id,
            entry_intent_id=entry_intent_id,
            broker_order_id=(
                str(approval_payload.get("broker_order_id"))
                if approval_payload.get("broker_order_id") not in (None, "")
                else None
            ),
            broker_tag=(
                str(approval_payload.get("broker_tag"))
                if approval_payload.get("broker_tag") not in (None, "")
                else None
            ),
            payload=dict(approval_payload),
            source="approval_route",
        )


def _resolve_pending_approval(
    payload: list[dict[str, object]],
    approval_id: str,
) -> tuple[int, PendingApproval, dict[str, object]]:
    normalized_identifier = approval_id.strip()
    for index, item in enumerate(payload):
        approval = PendingApproval.model_validate(item)
        normalized_item = approval.model_dump(mode="json")
        item.update(normalized_item)
        if normalized_item["approval_id"] == normalized_identifier:
            return index, approval, item
    raise HTTPException(status_code=404, detail="Pending approval not found")


def _is_expired(approval: PendingApproval) -> bool:
    expires_at = approval.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=IST)
    else:
        expires_at = expires_at.astimezone(IST)
    return expires_at <= datetime.now(IST)


def _load_approval_for_action(approval_id: str) -> tuple[PendingApproval, dict[str, object]]:
    stored: dict[str, object] | None = None
    with session_scope() as session:
        repo = MemoryRepository(session)
        payload = repo.get_pending_approvals_payload()
        try:
            _, approval, approval_payload = _resolve_pending_approval(payload, approval_id)
            return approval, approval_payload
        except HTTPException:
            stored = repo.get_approval(approval_id.strip())

    if stored is None:
        raise HTTPException(status_code=404, detail="Pending approval not found")
    approval = PendingApproval.model_validate(stored)
    approval_payload = approval.model_dump(mode="json")
    if not _is_expired(approval):
        raise HTTPException(status_code=404, detail="Pending approval not found")
    return approval, approval_payload


@router.get("", response_model=List[PendingApproval])
async def get_approvals():
    """List pending approvals."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        payload = repo.get_pending_approvals_payload()
    return [PendingApproval.model_validate(p) for p in payload]


@router.post("/{approval_id}/yes", response_model=ApprovalResponse)
async def approve_trade(approval_id: str):
    """Approve a trade setup."""
    live_entry_block_reason = runtime_flags.live_entry_block_reason(cfg.trading.mode)
    if live_entry_block_reason is None and cfg.trading.mode.value == "live" and not has_kite_session():
        live_entry_block_reason = "KITE_SESSION_REQUIRED"
    if live_entry_block_reason is None:
        live_entry_block_reason = new_entries_block_reason()
    approval, approval_payload = _load_approval_for_action(approval_id)

    if _is_expired(approval):
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.update_approval_payload(
                approval.approval_id,
                {
                    **approval_payload,
                    "approved": False,
                    "execution_requested": False,
                    "execution_request_id": None,
                    "status": "expired",
                },
                source="approval_route",
            )
        project_all_managed_files()
        return ApprovalResponse(
            approval_id=str(approval.approval_id),
            decision="expired",
            ticker=approval.ticker,
            message="Approval has expired. No execution was queued.",
        )

    if approval_payload.get("approved") is True and approval_payload.get("execution_requested") is True:
        _persist_order_intent(approval_payload, status="queued")
        return ApprovalResponse(
            approval_id=str(approval.approval_id),
            decision="approved",
            ticker=approval.ticker,
            message="Already approved. Execution is already queued.",
        )

    approval_payload["approved"] = True
    approval_payload["execution_requested"] = live_entry_block_reason is None
    approval_payload["execution_request_id"] = (
        str(approval.order_intent_id).rsplit(":", 1)[-1]
        if live_entry_block_reason is None
        else None
    )
    approval_payload["status"] = "queued" if live_entry_block_reason is None else "approved"

    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.update_approval_payload(
            approval.approval_id,
            approval_payload,
            source="approval_route",
        )
    project_all_managed_files()

    if live_entry_block_reason is None:
        message = "Approved. Queued for worker execution."
    else:
        message = (
            "Approved, but live execution is blocked by runtime guardrails "
            f"({live_entry_block_reason})."
        )
    await broadcaster.broadcast(
        "approvals_update", {"ticker": approval.ticker, "approval_id": approval.approval_id, "action": "approved"}
    )

    return ApprovalResponse(
        approval_id=str(approval.approval_id),
        decision="approved",
        ticker=approval.ticker,
        message=message,
    )


@router.post("/{approval_id}/no", response_model=ApprovalResponse)
async def reject_trade(approval_id: str):
    """Reject a trade setup."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        payload = repo.get_pending_approvals_payload()
    _, approval, approval_payload = _resolve_pending_approval(payload, approval_id)
    approval_payload["approved"] = False
    approval_payload["execution_requested"] = False
    approval_payload["execution_request_id"] = None
    approval_payload["status"] = "rejected"
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.update_approval_payload(
            approval.approval_id,
            approval_payload,
            source="approval_route",
        )
    project_all_managed_files()
    await broadcaster.broadcast(
        "approvals_update",
        {"ticker": approval.ticker, "approval_id": approval.approval_id, "action": "rejected"},
    )

    return ApprovalResponse(
        approval_id=str(approval.approval_id),
        decision="rejected",
        ticker=approval.ticker,
        message="Rejected and persisted for worker/audit visibility.",
    )
