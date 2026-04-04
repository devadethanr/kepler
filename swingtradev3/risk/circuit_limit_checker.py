from __future__ import annotations


def is_circuit_hit(position_price: float, upper_circuit: float | None, lower_circuit: float | None) -> bool:
    if upper_circuit is not None and position_price >= upper_circuit:
        return True
    if lower_circuit is not None and position_price <= lower_circuit:
        return True
    return False
