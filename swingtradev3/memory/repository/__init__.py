"""Memory Repository Package — Refactored from repositories.py.

Domain modules:
    account       — AccountStateRow (cash, PnL, positions payload)
    approvals     — ApprovalRow (pending/active/approved/queued approvals)
    broker        — BrokerOrderRow, BrokerFillRow, ProtectiveTriggerRow
    entry_intents — EntryIntentRow
    events        — ExecutionEventRow (append-only audit log)
    failure       — FailureIncidentRow
    news          — NewsArticleRow, NewsProviderHealthRow
    operator      — OperatorControlRow
    order_intents — OrderIntentRow
    policy        — PolicyOverlayRow
    positions     — PositionRow
    reconciliation — ReconciliationRunRow
    trades        — TradeRow

MemoryRepository aggregates all sub-repos and is the sole public API.
All 41 existing call sites import ``from memory.repository import MemoryRepository``
and continue to work via the shim at ``../repositories.py``.
"""

from .account import AccountRepository
from .approvals import ApprovalRepository
from .broker import BrokerRepository
from .entry_intents import EntryIntentRepository
from .events import EventRepository
from .failure import FailureRepository
from .news import NewsRepository
from .operator import OperatorRepository
from .order_intents import OrderIntentRepository
from .policy import PolicyRepository
from .positions import PositionRepository
from .reconciliation import ReconciliationRepository
from .trades import TradeRepository

# Re-export for backwards compatibility
from .memory_repository import MemoryRepository  # noqa: F401
from .events import EventRepository  # noqa: F401

# Re-export models that old code imports from memory.repositories
from ..models import StoredKiteSessionPayload  # noqa: F401