from __future__ import annotations

import asyncio
from datetime import datetime
import schedule
import time

from config import cfg

class TradingScheduler:
    def __init__(self):
        self.is_running = False
        self._task = None

    async def start(self):
        self.is_running = True
        
        # Phase 1: Overnight Monitoring
        # schedule.every(2).hours.do(self._run_overnight_tracking)
        
        # Phase 2: Pre-Market Preparation
        schedule.every().day.at(cfg.scheduler.morning.briefing_generation_time).do(self._generate_morning_briefing)
        
        # Phase 3: Market Hours Execution
        # Managed by execution agent polling loop currently, but could be integrated here
        
        # Phase 5: Evening Research Pipeline
        schedule.every().day.at(cfg.scheduler.evening_research.start_time).do(self._trigger_research_pipeline)
        
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while self.is_running:
            schedule.run_pending()
            await asyncio.sleep(1)

    def _generate_morning_briefing(self):
        print(f"[{datetime.now().isoformat()}] Triggering Morning Briefing...")
        from api.tasks.morning_briefing import generate_morning_briefing
        asyncio.create_task(generate_morning_briefing())

    def _trigger_research_pipeline(self):
        print(f"[{datetime.now().isoformat()}] Triggering Evening Research Pipeline...")
        # This calls the background task
        asyncio.create_task(self._run_research_bg())

    async def _run_research_bg(self):
        from api.routes.scan import run_research_pipeline_bg
        await run_research_pipeline_bg()

# Singleton
scheduler = TradingScheduler()
