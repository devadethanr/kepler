from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time

from config import cfg

# Very basic in-memory rate limiting
clients = {}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not cfg.api.enabled:
            return await call_next(request)
            
        client_ip = request.client.host
        now = time.time()
        
        # Initialize client limit
        if client_ip not in clients:
            clients[client_ip] = {"tokens": float(cfg.api.rate_limit.burst), "last_updated": now}
            
        # Refill tokens
        elapsed = now - clients[client_ip]["last_updated"]
        refill_rate = cfg.api.rate_limit.requests_per_minute / 60.0
        
        clients[client_ip]["tokens"] = min(
            float(cfg.api.rate_limit.burst),
            clients[client_ip]["tokens"] + elapsed * refill_rate
        )
        clients[client_ip]["last_updated"] = now
        
        if clients[client_ip]["tokens"] < 1.0:
            return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})
            
        clients[client_ip]["tokens"] -= 1.0
        
        response = await call_next(request)
        return response
