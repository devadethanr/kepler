from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from auth.kite.client import has_kite_session
from config import cfg, runtime_flags
from api.sse_broadcaster import broadcaster
from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import ApprovalResponse, PendingApproval
from paths import CONTEXT_DIR
from storage import read_json, write_json

router = APIRouter()


def _order_intent_id(ticker: str, request_id: str) -> str:
    return f"order-intent:{ticker.upper()}:{request_id}"


def _persist_order_intent(approval_payload: dict[str, object], *, status: str) -> None:
    order_intent_id = str(approval_payload.get("order_intent_id") or "").strip()
    ticker = str(approval_payload.get("ticker") or "").strip().upper()
    if not order_intent_id or not ticker:
        return
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status=status,
            broker_tag=(
                str(approval_payload.get("broker_tag"))
                if approval_payload.get("broker_tag") not in (None, "")
                else None
            ),
            payload=dict(approval_payload),
            source="approval_route",
        )


@router.get("", response_model=List[PendingApproval])
async def get_approvals():
    """List pending approvals."""
    payload = read_json(CONTEXT_DIR / "pending_approvals.json", [])
    return [PendingApproval.model_validate(p) for p in payload]


@router.post("/{ticker}/yes", response_model=ApprovalResponse)
async def approve_trade(ticker: str):
    """Approve a trade setup."""
    payload = read_json(CONTEXT_DIR / "pending_approvals.json", [])
    live_entry_block_reason = runtime_flags.live_entry_block_reason(cfg.trading.mode)
    if live_entry_block_reason is None and cfg.trading.mode.value == "live" and not has_kite_session():
        live_entry_block_reason = "KITE_SESSION_REQUIRED"

    for p in payload:
        if str(p.get("ticker")).lower() == ticker.lower():
            approval = PendingApproval.model_validate(p)
            if approval.expires_at <= datetime.now():
                return ApprovalResponse(
                    approval_id=f"app-{ticker}",
                    decision="expired",
                    ticker=approval.ticker,
                    message="Approval has expired. No execution was queued.",
                )

            if p.get("approved") is True and p.get("execution_requested") is True:
                order_intent_id = str(p.get("order_intent_id") or "").strip()
                if not order_intent_id:
                    request_id = str(p.get("execution_request_id") or uuid4().hex[:8])
                    order_intent_id = _order_intent_id(approval.ticker, request_id)
                    p["order_intent_id"] = order_intent_id
                    write_json(CONTEXT_DIR / "pending_approvals.json", payload)
                _persist_order_intent(p, status="queued")
                return ApprovalResponse(
                    approval_id=f"app-{ticker}",
                    decision="approved",
                    ticker=approval.ticker,
                    message="Already approved. Execution is already queued.",
                )

            request_id = uuid4().hex[:8]
            order_intent_id = str(p.get("order_intent_id") or _order_intent_id(approval.ticker, request_id))
            p["approved"] = True
            p["execution_requested"] = live_entry_block_reason is None
            p["execution_request_id"] = request_id if live_entry_block_reason is None else None
            p["order_intent_id"] = order_intent_id
            write_json(CONTEXT_DIR / "pending_approvals.json", payload)

            if live_entry_block_reason is None:
                _persist_order_intent(p, status="queued")
                message = "Approved. Queued for worker execution."
            else:
                _persist_order_intent(p, status="approved_blocked")
                message = (
                    "Approved, but live execution is blocked by runtime guardrails "
                    f"({live_entry_block_reason})."
                )
            await broadcaster.broadcast(
                "approvals_update", {"ticker": ticker, "action": "approved"}
            )

            return ApprovalResponse(
                approval_id=f"app-{ticker}",
                decision="approved",
                ticker=p.get("ticker", ticker),
                message=message,
            )

    raise HTTPException(status_code=404, detail="Pending approval not found")


@router.post("/{ticker}/no", response_model=ApprovalResponse)
async def reject_trade(ticker: str):
    """Reject a trade setup."""
    payload = read_json(CONTEXT_DIR / "pending_approvals.json", [])
    new_payload = []
    found = False

    for p in payload:
        if str(p.get("ticker")).lower() == ticker.lower():
            found = True
            _persist_order_intent(
                {
                    **p,
                    "ticker": p.get("ticker", ticker),
                    "order_intent_id": p.get("order_intent_id"),
                },
                status="rejected",
            )
        else:
            new_payload.append(p)

    if not found:
        raise HTTPException(status_code=404, detail="Pending approval not found")

    write_json(CONTEXT_DIR / "pending_approvals.json", new_payload)
    await broadcaster.broadcast("approvals_update", {"ticker": ticker, "action": "rejected"})

    return ApprovalResponse(
        approval_id=f"app-{ticker}",
        decision="rejected",
        ticker=ticker,
        message="Rejected and removed from pending approvals.",
    )
