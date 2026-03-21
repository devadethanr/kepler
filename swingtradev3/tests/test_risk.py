from swingtradev3.models import AccountState
from swingtradev3.risk.engine import SelfHealingRiskEngine


def test_risk_engine_approves_valid_trade() -> None:
    engine = SelfHealingRiskEngine()
    state = AccountState(cash_inr=20000.0)
    decision = engine.evaluate(state, score=8.2, entry_price=100.0, stop_price=95.0, target_price=110.0)
    assert decision.approved is True
    assert decision.quantity > 0


def test_risk_engine_rejects_bad_rr() -> None:
    engine = SelfHealingRiskEngine()
    state = AccountState(cash_inr=20000.0)
    decision = engine.evaluate(state, score=8.2, entry_price=100.0, stop_price=95.0, target_price=104.0)
    assert decision.approved is False
