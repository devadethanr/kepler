from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import (
    approvals,
    dashboard,
    health,
    portfolio,
    positions,
    postbacks,
    regime,
    scan,
    sse,
    stats,
    trades,
    ws,
)
from .middleware.auth import get_api_key

START_TIME = time.time()

def load_models():
    import logging
    try:
        from tools.analysis.sentiment_analysis import _get_finbert
        logging.getLogger("swingtradev3").info("Warming up FinBERT model...")
        _get_finbert()
        logging.getLogger("swingtradev3").info("FinBERT warmed up.")
    except Exception as e:
        logging.getLogger("swingtradev3").error(f"Failed to load FinBERT: {e}")

    try:
        from data.timesfm_forecaster import _get_timesfm_model
        logging.getLogger("swingtradev3").info("Warming up TimesFM model...")
        _get_timesfm_model()
        logging.getLogger("swingtradev3").info("TimesFM warmed up.")
    except Exception as e:
        logging.getLogger("swingtradev3").error(f"Failed to load TimesFM: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    from paths import ensure_runtime_dirs
    from memory.bootstrap import initialize_memory_layer
    import asyncio
    ensure_runtime_dirs()
    await asyncio.to_thread(initialize_memory_layer)
    
    # Warm up large models in the background so slow agent execution is purely inference
    asyncio.create_task(asyncio.to_thread(load_models))
    
    yield


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
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(postbacks.router, prefix="/broker/postbacks", tags=["Broker"])
app.include_router(sse.router, prefix="/sse", tags=["SSE"])
app.include_router(ws.router, tags=["WebSocket"])
