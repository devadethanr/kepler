from __future__ import annotations

import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import PendingApproval, ApprovalResponse

router = APIRouter()

@router.get("", response_model=List[PendingApproval])
async def get_approvals():
    """List pending approvals."""
    payload = read_json(CONTEXT_DIR / "pending_approvals.json", [])
    # Optionally filter out expired ones
    return [PendingApproval.model_validate(p) for p in payload]

@router.post("/{ticker}/yes", response_model=ApprovalResponse)
async def approve_trade(ticker: str):
    """Approve a trade setup."""
    payload = read_json(CONTEXT_DIR / "pending_approvals.json", [])
    for p in payload:
        if str(p.get("ticker")).lower() == ticker.lower():
            # In a real setup, we would trigger the order agent here
            # For now, mark as approved
            p["approved"] = True
            write_json(CONTEXT_DIR / "pending_approvals.json", payload)
            
            import asyncio
            from google.adk import Runner
            from google.adk.sessions import InMemorySessionService
            from agents.execution.order_agent import order_agent
            
            runner = Runner(
                app_name="swingtradev3",
                agent=order_agent,
                session_service=InMemorySessionService(),
                auto_create_session=True
            )
            
            # Run in background to not block the API
            async def run_order_bg():
                try:
                    async for _ in runner.run_async(user_id="system", session_id="order_session"):
                        pass
                except Exception as e:
                    print(f"Order agent failed: {e}")
                    
            asyncio.create_task(run_order_bg())
            
            return ApprovalResponse(
                approval_id=f"app-{ticker}",
                decision="approved",
                ticker=p.get("ticker", ticker),
                message="Approved. Execution agent triggered."
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
            # We just filter it out
        else:
            new_payload.append(p)
            
    if not found:
        raise HTTPException(status_code=404, detail="Pending approval not found")
        
    write_json(CONTEXT_DIR / "pending_approvals.json", new_payload)
    return ApprovalResponse(
        approval_id=f"app-{ticker}",
        decision="rejected",
        ticker=ticker,
        message="Rejected and removed from pending approvals."
    )
