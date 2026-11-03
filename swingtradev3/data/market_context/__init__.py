"""Read-only market context primitives; importing this package has no network effects."""

from data.market_context.snapshot import MarketSnapshot, assess

__all__ = ["MarketSnapshot", "assess"]
