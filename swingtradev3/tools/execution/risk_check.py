from __future__ import annotations

from models import AccountState
from risk.engine import SelfHealingRiskEngine


class RiskCheckTool:
    def __init__(self, engine: SelfHealingRiskEngine | None = None) -> None:
        self.engine = engine or SelfHealingRiskEngine()

    def check_risk(
        self,
        state: AccountState,
        score: float,
        entry_price: float,
        stop_price: float,
        target_price: float,
    ) -> dict[str, object]:
        decision = self.engine.evaluate(state, score, entry_price, stop_price, target_price)
        return {"approved": decision.approved, "quantity": decision.quantity, "reason": decision.reason}
