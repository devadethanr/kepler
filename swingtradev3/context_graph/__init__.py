"""Memgraph-backed context graph for research, memory, and learning.

Usage:
    from context_graph import ContextGraphRepository, ContextBuilder, GraphProjector

If Memgraph is unavailable, ContextGraphRepository raises GraphUnavailableError
and ContextBuilder returns empty/graceful defaults.  Trading safety is never
compromised.
"""

from .context_builder import ContextBuilder
from .projector import GraphProjector
from .repository import ContextGraphRepository, GraphUnavailableError

__all__ = [
    "ContextBuilder",
    "ContextGraphRepository",
    "GraphProjector",
    "GraphUnavailableError",
]