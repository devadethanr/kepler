from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json
from models import PendingApproval

async def generate_morning_briefing():
    """
    Summarizes the evening's research and pending approvals for the morning.
    """
    print(f"[{datetime.now().isoformat()}] Generating Morning Briefing...")
    
    # 1. Load pending approvals
    payload = read_json(CONTEXT_DIR / "pending_approvals.json", [])
    approvals = [PendingApproval.model_validate(p) for p in payload]
    
    if not approvals:
        message = "☀️ **Morning Briefing**\n\nNo high-conviction setups found in last night's scan."
    else:
        message = "☀️ **Morning Briefing**\n\n"
        message += f"Found {len(approvals)} setups ready for approval:\n\n"
        
        for app in approvals:
            message += f"🔹 **{app.ticker}** (Score: {app.score})\n"
            message += f"   Type: {app.setup_type}\n"
            message += f"   Entry: {app.entry_zone.low} - {app.entry_zone.high}\n"
            message += f"   Reason: {app.confidence_reasoning[:100]}...\n\n"
            
        message += "Reply YES {TICKER} to execute or go to the dashboard."

    # 2. In a real system, we'd fetch macro data here
    # 3. Send to Telegram (Logic to be added)
    print(f"DEBUG BRIEFING:\n{message}")
    
    return message
