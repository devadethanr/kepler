from __future__ import annotations

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from cognition.intraday import ExceptionAnalyst, ExceptionCase
from cognition.llm_client import CognitionLLMClient
from memory.db import session_scope
from memory.repository import MemoryRepository

IST = ZoneInfo("Asia/Kolkata")


async def _run() -> None:
    case = ExceptionCase(
        case_id=f"smoke:{datetime.now(IST).strftime('%Y%m%d%H%M%S%f')}",
        kind="broker_inconsistency",
        severity="warning",
        source="phase14_smoke",
        ticker="SBIN",
        summary="Synthetic broker/Postgres discrepancy for advisory-path verification.",
        evidence=[{"broker_quantity": 9, "postgres_quantity": 10, "synthetic": True}],
    )
    advice = await ExceptionAnalyst(
        llm_client=CognitionLLMClient(role="learning")
    ).analyze(case)
    run_id = f"exception:{case.case_id}"
    with session_scope() as session:
        repo = MemoryRepository(session)
        run = repo.get_cognition_run(run_id)
        reports = repo.list_cognition_reports(run_id=run_id, limit=10)

    if not advice.advisory_only:
        raise RuntimeError("Phase 14 advice escaped the advisory-only boundary")
    if run is None or run.get("status") != "completed" or not reports:
        raise RuntimeError("Phase 14 cognition audit records were not persisted")

    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": run["status"],
                "kind": advice.kind,
                "advisory_action": advice.advisory_action,
                "advisory_only": advice.advisory_only,
                "report_count": len(reports),
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    asyncio.run(_run())
