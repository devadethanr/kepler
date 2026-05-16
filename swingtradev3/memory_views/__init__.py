"""Phase 12 read-only memory views for LLM-facing agents."""

from .client import MemoryViewClient, get_memory_view_client

__all__ = ["MemoryViewClient", "get_memory_view_client"]
