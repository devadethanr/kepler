from __future__ import annotations

import asyncio
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from paths import CONTEXT_DIR
from storage import read_json
from models import ScanResult, ScanStatusResponse

router = APIRouter()

class ScanResponse(BaseModel):
    status: str
    message: str

# In-memory status tracker (should be moved to state/file in prod)
scan_status_store = {
    "status": "idle",
    "started_at": None,
    "completed_at": None,
}

async def run_research_pipeline_bg():
    """Wrapper to run the ADK research pipeline in background."""
    scan_status_store["status"] = "running"
    scan_status_store["started_at"] = datetime.utcnow()
    scan_status_store["completed_at"] = None

    try:
        from agents.research.pipeline import research_pipeline
        from google.adk import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types
        
        # We can use a simple in-memory session since results are saved to disk
        # by the ResultsSaverAgent.
        runner = Runner(
            app_name="swingtradev3",
            agent=research_pipeline,
            session_service=InMemorySessionService(),
            auto_create_session=True
        )
        
        async for event in runner.run_async(
            user_id="system", 
            session_id="scan_session", 
            new_message=types.Content(role="user", parts=[types.Part(text="Run research pipeline")])
        ):
            # Could stream events via websockets if needed
            pass
            
        scan_status_store["status"] = "completed"
    except Exception as e:
        scan_status_store["status"] = "failed"
        print(f"Research pipeline failed: {e}")
    finally:
        scan_status_store["completed_at"] = datetime.utcnow()

@router.post("", response_model=ScanResponse)
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger the research scan pipeline."""
    if scan_status_store["status"] == "running":
        return ScanResponse(status="rejected", message="Scan already running")
        
    background_tasks.add_task(run_research_pipeline_bg)
    return ScanResponse(status="accepted", message="Scan triggered in background")

@router.get("/status", response_model=ScanStatusResponse)
async def scan_status():
    """Get status of the latest scan."""
    result = None
    if scan_status_store["status"] == "completed":
        try:
            # We can load the latest scan result if available
            # It's stored in context/research/YYYY-MM-DD/scan_result.json
            import os
            research_dir = CONTEXT_DIR / "research"
            if research_dir.exists():
                # Find most recent date dir
                dirs = sorted([d for d in research_dir.iterdir() if d.is_dir()], reverse=True)
                if dirs:
                    latest = read_json(dirs[0] / "scan_result.json", None)
                    if latest:
                        result = ScanResult.model_validate(latest)
        except Exception:
            pass

    return ScanStatusResponse(
        status=scan_status_store["status"],
        started_at=scan_status_store["started_at"],
        completed_at=scan_status_store["completed_at"],
        result=result
    )
