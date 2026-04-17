from __future__ import annotations

from datetime import datetime

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.execution.order_agent import OrderExecutionAgent
from memory.db import session_scope
from memory.repositories import MemoryRepository


class WorkerExecutionStateMachine:
    def pending_execution_requests(self) -> list[dict[str, object]]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            approvals = repo.get_execution_requested_approvals()
        now = datetime.now()
        return [
            approval
            for approval in approvals
            if approval.get("approved") is True
            and datetime.fromisoformat(str(approval["expires_at"])) > now
        ]

    async def execute_requested_approvals(self) -> int:
        queued = self.pending_execution_requests()
        if not queued:
            return 0

        request_ids = sorted(
            str(approval.get("execution_request_id") or approval["ticker"]).lower() for approval in queued
        )
        runner = Runner(
            app_name="swingtradev3",
            agent=OrderExecutionAgent(),
            session_service=InMemorySessionService(),
            auto_create_session=True,
        )
        async for _ in runner.run_async(
            user_id="worker",
            session_id=f"worker_execution_{'_'.join(request_ids)}",
            new_message=types.Content(
                role="user",
                parts=[types.Part(text="Execute queued approvals from worker")],
            ),
        ):
            pass
        return len(queued)
