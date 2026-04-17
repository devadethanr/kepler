from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from .db import session_scope
from .projections import APPROVALS_PATH, KITE_SESSION_PATH, STATE_PATH, TRADES_PATH, project_all_managed_files
from .repositories import MemoryRepository


MANAGED_PATHS = {
    STATE_PATH.resolve(): "state",
    TRADES_PATH.resolve(): "trades",
    APPROVALS_PATH.resolve(): "approvals",
    KITE_SESSION_PATH.resolve(): "auth_session",
}

_bootstrap_lock = Lock()
_memory_initialized = False


def _read_raw_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _managed_key(path: Path) -> str | None:
    return MANAGED_PATHS.get(path.resolve())


def is_managed_path(path: Path) -> bool:
    return _managed_key(path) is not None


def initialize_memory_layer(force: bool = False) -> None:
    global _memory_initialized
    if _memory_initialized and not force:
        return

    with _bootstrap_lock:
        if _memory_initialized and not force:
            return

        with session_scope() as session:
            repo = MemoryRepository(session)
            if force or not repo.account_state_exists():
                repo.replace_account_state(
                    _read_raw_json(STATE_PATH, {}),
                    source="bootstrap_import",
                )
            if force or not repo.approvals_exist():
                repo.replace_pending_approvals(
                    _read_raw_json(APPROVALS_PATH, []),
                    source="bootstrap_import",
                )
            if force or not repo.trades_exist():
                repo.replace_trades(
                    _read_raw_json(TRADES_PATH, []),
                    source="bootstrap_import",
                )
            auth_payload = _read_raw_json(KITE_SESSION_PATH, {})
            if auth_payload and (force or not repo.auth_session_exists()):
                repo.replace_auth_session(
                    auth_payload,
                    source="bootstrap_import",
                )

        project_all_managed_files()
        _memory_initialized = True


def read_managed_json(path: Path, default: Any) -> Any:
    key = _managed_key(path)
    if key is None:
        raise KeyError(f"Unmanaged path: {path}")

    initialize_memory_layer()
    with session_scope() as session:
        repo = MemoryRepository(session)
        if key == "state":
            return repo.get_account_state_payload()
        if key == "trades":
            return repo.get_trades_payload()
        if key == "approvals":
            return repo.get_pending_approvals_payload()
        if key == "auth_session":
            payload = repo.get_auth_session_payload()
            return payload or default
    return default


def write_managed_json(path: Path, payload: Any) -> None:
    key = _managed_key(path)
    if key is None:
        raise KeyError(f"Unmanaged path: {path}")

    initialize_memory_layer()
    with session_scope() as session:
        repo = MemoryRepository(session)
        if key == "state":
            repo.replace_account_state(payload, source="legacy_write")
        elif key == "trades":
            repo.replace_trades(payload, source="legacy_write")
        elif key == "approvals":
            repo.replace_pending_approvals(payload, source="legacy_write")
        elif key == "auth_session":
            repo.replace_auth_session(payload, source="legacy_write")

    project_all_managed_files()
