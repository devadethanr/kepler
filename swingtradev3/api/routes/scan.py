from __future__ import annotations

import asyncio
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import ScanResult, ScanStatusResponse

router = APIRouter()

class ScanResponse(BaseModel):
    status: str
    message: str

# Concurrency guard — prevents parallel scan corruption
_scan_lock = asyncio.Lock()

# Persisted status tracker
_STATUS_FILE = CONTEXT_DIR / "scan_status.json"
_DEFAULT_STATUS = {
    "status": "idle",
    "started_at": None,
    "completed_at": None,
}

def _load_status() -> dict:
    """Load scan status from disk (survives restarts)."""
    return read_json(_STATUS_FILE, _DEFAULT_STATUS.copy())

def _save_status(status: dict) -> None:
    """Persist scan status to disk."""
    write_json(_STATUS_FILE, status)


async def run_research_pipeline_bg():
    """Wrapper to run the ADK research pipeline in background."""
    async with _scan_lock:
        status = _load_status()
        status["status"] = "running"
        status["started_at"] = datetime.now().isoformat()
        status["completed_at"] = None
        _save_status(status)

        try:
            from agents.research.pipeline import research_pipeline
            from google.adk import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types
            
            # Unique session ID per scan to prevent state contamination
            session_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            runner = Runner(
                app_name="swingtradev3",
                agent=research_pipeline,
                session_service=InMemorySessionService(),
                auto_create_session=True
            )
            
            async for event in runner.run_async(
                user_id="system", 
                session_id=session_id,
                new_message=types.Content(role="user", parts=[types.Part(text="Run research pipeline")])
            ):
                # Could stream events via websockets if needed
                pass
                
            status["status"] = "completed"
        except Exception as e:
            status["status"] = "failed"
            status["error"] = str(e)
            print(f"Research pipeline failed: {e}")
        finally:
            status["completed_at"] = datetime.now().isoformat()
            _save_status(status)

@router.post("", response_model=ScanResponse)
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger the research scan pipeline."""
    status = _load_status()
    if status["status"] == "running":
        return ScanResponse(status="rejected", message="Scan already running")

    if _scan_lock.locked():
        return ScanResponse(status="rejected", message="Scan already running (locked)")
        
    background_tasks.add_task(run_research_pipeline_bg)
    return ScanResponse(status="accepted", message="Scan triggered in background")

@router.get("/status", response_model=ScanStatusResponse)
async def scan_status():
    """Get status of the latest scan."""
    status = _load_status()
    result = None
    if status["status"] == "completed":
        try:
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
        status=status["status"],
        started_at=status.get("started_at"),
        completed_at=status.get("completed_at"),
        result=result
    )
