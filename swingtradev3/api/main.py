from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import health, ws, positions, trades, approvals, scan, regime, stats
from .tasks.scheduler import scheduler
from .middleware.auth import get_api_key

START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    from paths import ensure_runtime_dirs
    ensure_runtime_dirs()
    await scheduler.start()
    yield
    # Shutdown
    await scheduler.stop()


app = FastAPI(
    title="swingtradev3 API",
    description="Autonomous Swing Trading System API",
    version="2.0.0",
    lifespan=lifespan,
    dependencies=[Depends(get_api_key)]
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("swingtradev3").error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8502",
        "http://localhost:3000",
        "http://127.0.0.1:8502",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(positions.router, prefix="/positions", tags=["Positions"])
app.include_router(trades.router, prefix="/trades", tags=["Trades"])
app.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
app.include_router(scan.router, prefix="/scan", tags=["Scan"])
app.include_router(regime.router, prefix="/regime", tags=["Regime"])
app.include_router(stats.router, prefix="/stats", tags=["Stats"])
app.include_router(ws.router, tags=["WebSocket"])
