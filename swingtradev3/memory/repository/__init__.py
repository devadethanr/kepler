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
    cognition     — CognitionRunRow, CognitionReportRow, SessionExecutionPlanRow
    reconciliation — ReconciliationRunRow
    trades        — TradeRow

MemoryRepository aggregates all sub-repos and is the sole public API.
All existing call sites import ``from memory.repository import MemoryRepository``.
"""

from .account import AccountRepository
from .approvals import ApprovalRepository
from .broker import BrokerRepository
from .cognition import CognitionRepository
from .entry_intents import EntryIntentRepository
from .events import EventRepository
from .failure import FailureRepository
from .news import NewsRepository
from .operator import OperatorRepository
from .order_intents import OrderIntentRepository
from .policy import PolicyRepository
from .positions import PositionRepository
from .reconciliation import ReconciliationRepository
from .scan import ScanRepository
from .trades import TradeRepository

# Re-export for backwards compatibility
from .memory_repository import MemoryRepository  # noqa: F401
from .events import EventRepository  # noqa: F401

# Re-export models that old code imports from memory.repositories
from ..models import StoredKiteSessionPayload  # noqa: F401
