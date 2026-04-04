from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, ws

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    from paths import ensure_runtime_dirs
    ensure_runtime_dirs()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="swingtradev3 API",
    description="Autonomous Swing Trading System API",
    version="2.0.0",
    lifespan=lifespan,
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
app.include_router(ws.router, tags=["WebSocket"])
