from __future__ import annotations

import asyncio
from datetime import datetime
from typing import List

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json
from models import PendingApproval

async def _get_ngrok_url() -> str:
    """Read ngrok URL from persisted file, return empty if not available."""
    url_file = CONTEXT_DIR / "ngrok_url.txt"
    if url_file.exists():
        return url_file.read_text().strip()
    return "http://localhost:8502"

async def generate_morning_briefing():
    """
    Summarizes the evening's research and pending approvals for the morning.
    Sends the briefing via Telegram with a dashboard link.
    """
    print(f"[{datetime.now().isoformat()}] Generating Morning Briefing...")
    
    dashboard_url = await _get_ngrok_url()
    
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
            
        message += f"Review & approve on dashboard."

    # Add dashboard link
    message += f"\n\n📊 Dashboard: {dashboard_url}/approvals"

    # 2. Send via Telegram
    try:
        from notifications.telegram_client import TelegramClient
        tg = TelegramClient()
        await tg.send_briefing(message)
        print(f"Morning briefing sent to Telegram")
    except Exception as e:
        print(f"Failed to send morning briefing to Telegram: {e}")
    
    print(f"DEBUG BRIEFING:\n{message}")
    
    return message
