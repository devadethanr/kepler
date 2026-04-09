from __future__ import annotations

from contextlib import AsyncExitStack
import os
from typing import Any


def _normalize_tool_result(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    content = getattr(result, "content", [])
    normalized: list[dict[str, Any]] = []
    for item in content:
        entry: dict[str, Any] = {"type": getattr(item, "type", "unknown")}
        if hasattr(item, "text"):
            entry["text"] = item.text
        if hasattr(item, "data"):
            entry["data"] = item.data
        normalized.append(entry)
    return {"content": normalized}


class KiteMCPSession:
    def __init__(self, url: str) -> None:
        self.url = url
        self._stack = AsyncExitStack()
        self._session: Any | None = None

    async def __aenter__(self) -> "KiteMCPSession":
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client
        except ImportError as exc:
            raise RuntimeError("mcp package is required for Kite MCP integration") from exc

        transport = await self._stack.enter_async_context(streamable_http_client(self.url))
        read_stream, write_stream = transport[:2]
        self._session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._session = None
        await self._stack.aclose()

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("MCP session is not initialized")
        result = await self._session.call_tool(name, arguments=arguments or {})
        return _normalize_tool_result(result)


class KiteMCPClient:
    def __init__(self, url: str | None = None) -> None:
        self.url = url or os.getenv("KITE_MCP_URL", "http://kite-mcp:8080/mcp")

    def session(self) -> KiteMCPSession:
        return KiteMCPSession(self.url)

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        async with self.session() as session:
            return await session.call_tool(name, arguments=arguments or {})
