"""Phase 12 local smoke checks for curated memory views."""

from __future__ import annotations

from memory_views import MemoryViewClient


def main() -> None:
    client = MemoryViewClient()
    portfolio = client.portfolio_risk_snapshot()
    readiness = client.session_readiness()
    incidents = client.execution_incidents(limit=5)
    regime = client.regime_snapshot_context(limit=2)
    print(
        {
            "portfolio_view": bool(portfolio),
            "session_readiness_view": bool(readiness),
            "incident_rows": len(incidents),
            "regime_context_rows": len(regime),
            "status": "ok",
        }
    )


if __name__ == "__main__":
    main()
