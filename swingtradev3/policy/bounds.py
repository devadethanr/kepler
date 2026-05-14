from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from policy.models import PolicyKey


ALLOWED_POLICY_KEYS: set[str] = {
    "min_score_threshold",
    "max_position_size_pct",
    "new_entries_enabled",
    "max_same_sector_positions",
    "trail_stop_at_pct",
    "trail_to_pct",
    "debate_top_n",
}


NUMERIC_BOUNDS: dict[str, tuple[float, float]] = {
    "min_score_threshold": (5.0, 10.0),
    "max_position_size_pct": (1.0, 50.0),
    "max_same_sector_positions": (1.0, 5.0),
    "trail_stop_at_pct": (1.0, 20.0),
    "trail_to_pct": (2.0, 40.0),
    "debate_top_n": (1.0, 10.0),
}

INTEGER_KEYS = {"max_same_sector_positions", "debate_top_n"}


class PolicyValidationError(ValueError):
    pass


def canonical_value(raw: Any) -> Any:
    if isinstance(raw, Mapping) and set(raw.keys()) == {"value"}:
        return raw["value"]
    return raw


def validate_policy_key(key: str) -> PolicyKey:
    normalized = key.strip()
    if normalized not in ALLOWED_POLICY_KEYS:
        raise PolicyValidationError(f"policy key is not allowed: {key}")
    return normalized  # type: ignore[return-value]


def validate_policy_value(
    key: str,
    value: Any,
    *,
    current_policy: Mapping[str, Any] | None = None,
) -> Any:
    normalized_key = validate_policy_key(key)
    raw_value = canonical_value(value)

    if normalized_key == "new_entries_enabled":
        if not isinstance(raw_value, bool):
            raise PolicyValidationError("new_entries_enabled must be a boolean")
        return raw_value

    if normalized_key not in NUMERIC_BOUNDS:
        raise PolicyValidationError(f"policy key has no configured bounds: {normalized_key}")

    try:
        numeric = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise PolicyValidationError(f"{normalized_key} must be numeric") from exc

    minimum, maximum = NUMERIC_BOUNDS[normalized_key]
    if numeric < minimum or numeric > maximum:
        raise PolicyValidationError(
            f"{normalized_key} must be between {minimum:g} and {maximum:g}"
        )

    if normalized_key in INTEGER_KEYS:
        if int(numeric) != numeric:
            raise PolicyValidationError(f"{normalized_key} must be an integer")
        normalized_value: Any = int(numeric)
    else:
        normalized_value = numeric

    if current_policy:
        trail_stop = float(current_policy.get("trail_stop_at_pct", 0.0))
        trail_to = float(current_policy.get("trail_to_pct", 0.0))
        if normalized_key == "trail_stop_at_pct":
            trail_stop = float(normalized_value)
        elif normalized_key == "trail_to_pct":
            trail_to = float(normalized_value)
        if trail_stop and trail_to and trail_to <= trail_stop:
            raise PolicyValidationError("trail_to_pct must be greater than trail_stop_at_pct")

    return normalized_value
