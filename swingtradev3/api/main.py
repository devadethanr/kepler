from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, ws, positions, trades, approvals, scan, regime, stats
from .tasks.scheduler import scheduler
from .middleware.auth import get_api_key
from fastapi import Depends

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
