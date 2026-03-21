from __future__ import annotations

import os
from typing import Any


class KiteMCPClient:
    def __init__(self, url: str | None = None) -> None:
        self.url = url or os.getenv("KITE_MCP_URL", "http://kite-mcp:8080/mcp")

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client
        except ImportError as exc:
            raise RuntimeError("mcp package is required for Kite MCP integration") from exc

        async with streamable_http_client(self.url) as transport:
            read_stream, write_stream = transport[:2]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments=arguments or {})
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
