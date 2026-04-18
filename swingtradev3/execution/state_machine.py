from __future__ import annotations

from .coordinator import ExecutionCoordinator


class WorkerExecutionStateMachine:
    def __init__(self, coordinator: ExecutionCoordinator | None = None) -> None:
        self.coordinator = coordinator or ExecutionCoordinator()

    def pending_execution_requests(self) -> list[dict[str, object]]:
        return self.coordinator.pending_execution_requests()

    async def execute_requested_approvals(self) -> int:
        return await self.coordinator.submit_queued_order_intents()

    async def advance_active_executions(self) -> int:
        return await self.coordinator.reconcile_active_order_intents()
