from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paths import CONTEXT_DIR, ensure_runtime_dirs

from .db import session_scope
from .repositories import MemoryRepository


STATE_PATH = CONTEXT_DIR / "state.json"
TRADES_PATH = CONTEXT_DIR / "trades.json"
APPROVALS_PATH = CONTEXT_DIR / "pending_approvals.json"
KITE_SESSION_PATH = CONTEXT_DIR / "auth" / "kite_session.json"


def _write_projection_file(path: Path, payload: Any) -> None:
    ensure_runtime_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)


def project_all_managed_files() -> None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        _write_projection_file(STATE_PATH, repo.get_account_state_payload())
        _write_projection_file(TRADES_PATH, repo.get_trades_payload())
        _write_projection_file(APPROVALS_PATH, repo.get_pending_approvals_payload())
        auth_payload = repo.get_auth_session_payload()
        if auth_payload:
            _write_projection_file(KITE_SESSION_PATH, auth_payload)
