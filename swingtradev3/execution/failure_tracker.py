"""Phase 7: shared consecutive-failure counter.

Used by ``coordinator`` (order-submission failures) and ``protection_manager``
(GTT-recovery failures). The reconciler's loop counters predate this helper and
continue to use their bespoke in-class implementation.

Every counter is in-memory per-process (no DB round trip) which matches the
Phase 6 reconciler pattern (`_consecutive_failures: dict[str, int]`). Persisted
state lives in the incidents table + ``block_new_entries`` control — the
counter itself is a tiny bookkeeping object.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FailureCounter:
    """Tiny in-memory consecutive-failure counter.

    Usage:
        self._order_failures = FailureCounter(threshold=3)
        ...
        if self._order_failures.record_failure():
            set_block_new_entries(reason="order_submission_failures", ...)
        ...
        if self._order_failures.record_success():
            clear_block_new_entries(reason="order_submission_failures", ...)
    """

    threshold: int
    count: int = 0
    _already_tripped: bool = False

    def record_failure(self) -> bool:
        """Increment and return True iff this increment crosses the threshold.

        Returns False once the counter is already in the tripped state — caller
        does not need to re-alert on every subsequent failure.
        """
        self.count += 1
        if self.count >= self.threshold and not self._already_tripped:
            self._already_tripped = True
            return True
        return False

    def record_success(self) -> bool:
        """Reset to zero. Returns True iff this clears a tripped counter."""
        was_tripped = self._already_tripped
        self.count = 0
        self._already_tripped = False
        return was_tripped

    def is_tripped(self) -> bool:
        return self._already_tripped
