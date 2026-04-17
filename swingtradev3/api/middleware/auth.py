from __future__ import annotations

from fastapi import Request, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

from config import cfg

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(request: Request, api_key_header: str = Security(api_key_header)):
    if request.url.path == "/health" or request.url.path.startswith("/broker/postbacks/"):
        return True
        
    if not cfg.api.enabled:
        return True
        
    expected_api_key = cfg.api.api_key
    if not expected_api_key:
        # If no API key configured, we allow access but this should ideally be disabled in prod
        return True

    if api_key_header == expected_api_key:
        return api_key_header
        
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN, detail="Could not validate API KEY"
    )
