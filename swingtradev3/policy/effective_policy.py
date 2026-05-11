from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from config import cfg
from memory.db import session_scope
from memory.repositories import MemoryRepository
from policy.bounds import PolicyValidationError, canonical_value, validate_policy_value
from policy.models import AppliedOverlay, EffectivePolicy, IgnoredOverlay

IST = ZoneInfo("Asia/Kolkata")
ACTIVE_OVERLAY_STATUSES = {"active", "approved"}


def _now_ist() -> datetime:
    return datetime.now(IST)


def _parse_expiry(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST)


def _base_max_position_size_pct() -> float:
    configured = getattr(cfg.risk, "max_position_size_pct", None)
    if configured is not None:
        return float(configured)
    return max(
        float(cfg.risk.confidence_sizing.high.capital_pct),
        float(cfg.risk.confidence_sizing.medium.capital_pct),
    ) * 100.0


def build_base_policy() -> dict[str, Any]:
    return {
        "min_score_threshold": float(cfg.research.min_score_threshold),
        "max_position_size_pct": _base_max_position_size_pct(),
        "new_entries_enabled": True,
        "max_same_sector_positions": int(cfg.research.max_same_sector_positions),
        "trail_stop_at_pct": float(cfg.execution.trail_stop_at_pct),
        "trail_to_pct": float(cfg.execution.trail_to_pct),
        "debate_top_n": int(getattr(cfg.research, "debate_top_n", 3)),
    }


def resolve_effective_policy() -> EffectivePolicy:
    resolved_at = _now_ist()
    base = build_base_policy()
    values = dict(base)
    sources = {key: "config" for key in values}
    applied: list[AppliedOverlay] = []
    ignored: list[IgnoredOverlay] = []

    with session_scope() as session:
        repo = MemoryRepository(session)
        overlays = repo.list_policy_overlays()

    for overlay in overlays:
        overlay_id = str(overlay.get("overlay_id") or "")
        key = str(overlay.get("key") or "")
        status = str(overlay.get("status") or "").lower()
        payload = dict(overlay.get("payload") or {})
        if status not in ACTIVE_OVERLAY_STATUSES:
            continue

        expires_at = _parse_expiry(payload.get("expires_at"))
        if expires_at is not None and expires_at <= resolved_at:
            ignored.append(IgnoredOverlay(overlay_id=overlay_id, key=key, reason="expired"))
            continue

        try:
            value = validate_policy_value(
                key,
                canonical_value(overlay.get("value")),
                current_policy=values,
            )
        except PolicyValidationError as exc:
            ignored.append(IgnoredOverlay(overlay_id=overlay_id, key=key, reason=str(exc)))
            continue

        values[key] = value
        sources[key] = f"policy_overlay:{overlay_id}"
        applied.append(
            AppliedOverlay(
                overlay_id=overlay_id,
                key=key,
                value=value,
                reason=str(payload.get("reason") or ""),
                proposer=str(payload.get("proposer") or ""),
                approver=payload.get("approver"),
                expires_at=payload.get("expires_at"),
            )
        )

    from execution.operator_controls import read_new_entries_enabled

    operator_record = read_new_entries_enabled()
    operator_controls: dict[str, Any] = {}
    if operator_record is not None:
        operator_controls["new_entries_enabled"] = operator_record
        if not bool(operator_record.get("enabled", True)):
            values["new_entries_enabled"] = False
            sources["new_entries_enabled"] = "operator_control:new_entries_enabled"

    return EffectivePolicy(
        min_score_threshold=float(values["min_score_threshold"]),
        max_position_size_pct=float(values["max_position_size_pct"]),
        new_entries_enabled=bool(values["new_entries_enabled"]),
        max_same_sector_positions=int(values["max_same_sector_positions"]),
        trail_stop_at_pct=float(values["trail_stop_at_pct"]),
        trail_to_pct=float(values["trail_to_pct"]),
        debate_top_n=int(values["debate_top_n"]),
        base=base,
        sources=sources,
        applied_overlays=applied,
        ignored_overlays=ignored,
        operator_controls=operator_controls,
        resolved_at_ist=resolved_at,
    )


def new_entries_block_reason() -> str | None:
    policy = resolve_effective_policy()
    if policy.new_entries_enabled:
        return None
    return f"{policy.sources.get('new_entries_enabled', 'effective_policy')}:new_entries_enabled=false"
