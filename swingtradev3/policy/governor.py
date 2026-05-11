from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from memory.db import session_scope
from memory.repository import MemoryRepository
from policy.bounds import PolicyValidationError, validate_policy_key, validate_policy_value
from policy.effective_policy import build_base_policy
from policy.models import PolicyOverlay

IST = ZoneInfo("Asia/Kolkata")
TERMINAL_STATUSES = {"rejected", "expired", "rolled_back"}


def _now_ist() -> datetime:
    return datetime.now(IST)


def _now_iso() -> str:
    return _now_ist().isoformat()


def _parse_expiry(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PolicyValidationError("expires_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST).isoformat()


def _overlay_from_row(row: dict[str, Any]) -> PolicyOverlay:
    payload = dict(row.get("payload") or {})
    raw_value = row.get("value")
    if isinstance(raw_value, dict) and set(raw_value.keys()) == {"value"}:
        value = raw_value["value"]
    else:
        value = raw_value
    return PolicyOverlay(
        overlay_id=str(row["overlay_id"]),
        key=validate_policy_key(str(row["key"])),
        value=value,
        status=str(row["status"]),
        reason=str(payload.get("reason") or ""),
        proposer=str(payload.get("proposer") or ""),
        approver=payload.get("approver"),
        expires_at=payload.get("expires_at"),
        rollback_handle=str(payload.get("rollback_handle") or row["overlay_id"]),
        payload=payload,
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


class PolicyGovernor:
    def propose_overlay(
        self,
        *,
        key: str,
        value: Any,
        reason: str,
        proposer: str,
        expires_at: str | None = None,
        overlay_id: str | None = None,
        rollback_handle: str | None = None,
    ) -> PolicyOverlay:
        normalized_key = validate_policy_key(key)
        normalized_value = validate_policy_value(
            normalized_key,
            value,
            current_policy=build_base_policy(),
        )
        normalized_expiry = _parse_expiry(expires_at)
        normalized_id = overlay_id or f"policy-{uuid4().hex[:12]}"
        handle = rollback_handle or f"rollback:{normalized_id}"
        now = _now_iso()
        payload = {
            "reason": reason.strip(),
            "proposer": proposer.strip(),
            "approver": None,
            "expires_at": normalized_expiry,
            "rollback_handle": handle,
            "history": [
                {
                    "event": "proposed",
                    "actor": proposer.strip(),
                    "reason": reason.strip(),
                    "at": now,
                }
            ],
        }
        if not payload["reason"]:
            raise PolicyValidationError("reason is required")
        if not payload["proposer"]:
            raise PolicyValidationError("proposer is required")

        with session_scope() as session:
            repo = MemoryRepository(session)
            row = repo.upsert_policy_overlay(
                overlay_id=normalized_id,
                key=normalized_key,
                value={"value": normalized_value},
                status="proposed",
                payload=payload,
                source="policy_governor",
            )
        return _overlay_from_row(row)

    def approve_overlay(
        self,
        overlay_id: str,
        *,
        approver: str,
        reason: str | None = None,
    ) -> PolicyOverlay:
        if not approver.strip():
            raise PolicyValidationError("approver is required")
        with session_scope() as session:
            repo = MemoryRepository(session)
            row = repo.get_policy_overlay(overlay_id)
            if row is None:
                raise KeyError(overlay_id)
            status = str(row.get("status") or "").lower()
            if status in TERMINAL_STATUSES:
                raise PolicyValidationError(f"cannot approve overlay in status {status}")
            payload = dict(row.get("payload") or {})
            validate_policy_value(
                str(row.get("key") or ""),
                row.get("value"),
                current_policy=build_base_policy(),
            )
            history = list(payload.get("history") or [])
            history.append(
                {
                    "event": "approved",
                    "actor": approver.strip(),
                    "reason": reason,
                    "at": _now_iso(),
                }
            )
            payload.update({"approver": approver.strip(), "approved_at": _now_iso(), "history": history})
            updated = repo.transition_policy_overlay_status(
                overlay_id,
                status="active",
                payload_updates=payload,
                source="policy_governor",
            )
        return _overlay_from_row(updated)

    def reject_overlay(
        self,
        overlay_id: str,
        *,
        actor: str,
        reason: str,
    ) -> PolicyOverlay:
        return self._transition_terminal(
            overlay_id,
            status="rejected",
            actor=actor,
            reason=reason,
            event="rejected",
        )

    def rollback_overlay(
        self,
        overlay_id: str,
        *,
        actor: str,
        reason: str,
    ) -> PolicyOverlay:
        return self._transition_terminal(
            overlay_id,
            status="rolled_back",
            actor=actor,
            reason=reason,
            event="rolled_back",
        )

    def expire_overlay(
        self,
        overlay_id: str,
        *,
        actor: str = "policy_governor",
        reason: str = "expired",
    ) -> PolicyOverlay:
        return self._transition_terminal(
            overlay_id,
            status="expired",
            actor=actor,
            reason=reason,
            event="expired",
        )

    def _transition_terminal(
        self,
        overlay_id: str,
        *,
        status: str,
        actor: str,
        reason: str,
        event: str,
    ) -> PolicyOverlay:
        if not actor.strip():
            raise PolicyValidationError("actor is required")
        if not reason.strip():
            raise PolicyValidationError("reason is required")
        with session_scope() as session:
            repo = MemoryRepository(session)
            row = repo.get_policy_overlay(overlay_id)
            if row is None:
                raise KeyError(overlay_id)
            payload = dict(row.get("payload") or {})
            history = list(payload.get("history") or [])
            history.append(
                {
                    "event": event,
                    "actor": actor.strip(),
                    "reason": reason.strip(),
                    "at": _now_iso(),
                }
            )
            payload.update(
                {
                    f"{event}_at": _now_iso(),
                    f"{event}_by": actor.strip(),
                    f"{event}_reason": reason.strip(),
                    "history": history,
                }
            )
            updated = repo.transition_policy_overlay_status(
                overlay_id,
                status=status,
                payload_updates=payload,
                source="policy_governor",
            )
        return _overlay_from_row(updated)

    def get_overlay(self, overlay_id: str) -> PolicyOverlay | None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            row = repo.get_policy_overlay(overlay_id)
        return _overlay_from_row(row) if row is not None else None

    def list_overlays(
        self,
        *,
        status: str | None = None,
        key: str | None = None,
    ) -> list[PolicyOverlay]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            rows = repo.list_policy_overlays(status=status, key=key)
        return [_overlay_from_row(row) for row in rows]
