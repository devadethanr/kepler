"""Authenticated relay from the Docker API to the host research API over a local socket."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

from api.middleware.auth import get_api_key

router = APIRouter(dependencies=[Depends(get_api_key)])


@router.api_route("/{path:path}", methods=["GET", "POST"])
async def relay_research(path: str, request: Request):
    socket_path = os.getenv("KEPLER_RESEARCH_SOCKET", "")
    if not socket_path:
        raise HTTPException(503, "Local research service is not configured")
    if any(part in (".", "..") for part in path.split("/")):
        raise HTTPException(400, "Invalid research route")
    transport = httpx.AsyncHTTPTransport(uds=socket_path)
    client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(10, read=None))
    headers = {
        key: request.headers[key]
        for key in ("x-api-key", "content-type", "accept", "last-event-id")
        if key in request.headers
    }
    url = "http://research/research/" + path
    if request.url.query:
        url += "?" + request.url.query
    try:
        upstream = await client.send(
            client.build_request(
                request.method, url, headers=headers, content=await request.body()
            ),
            stream=True,
        )
    except httpx.TransportError as exc:
        await client.aclose()
        raise HTTPException(
            503, "Local research service is unavailable; start research services"
        ) from exc
    response_headers = {
        key: upstream.headers[key]
        for key in ("content-type", "cache-control", "x-accel-buffering")
        if key in upstream.headers
    }
    if "text/event-stream" not in upstream.headers.get("content-type", ""):
        try:
            return Response(
                await upstream.aread(), status_code=upstream.status_code, headers=response_headers
            )
        finally:
            await upstream.aclose()
            await client.aclose()

    async def events():
        try:
            async for chunk in upstream.aiter_raw():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(events(), status_code=upstream.status_code, headers=response_headers)
