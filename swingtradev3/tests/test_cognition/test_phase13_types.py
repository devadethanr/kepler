from __future__ import annotations

from cognition.types import EntryZoneModel, FinalIntentDecision


def test_entry_zone_normalizes_low_high_order():
    zone = EntryZoneModel(low=110, high=100)
    assert zone.low == 100
    assert zone.high == 110


def test_final_intent_status_mapping():
    actionable = FinalIntentDecision(ticker="SBIN", decision="BUY_ONLY_ABOVE_TRIGGER")
    watching = FinalIntentDecision(ticker="SBIN", decision="WAIT_FOR_PULLBACK")
    rejected = FinalIntentDecision(ticker="SBIN", decision="AVOID_NO_TRADE")

    assert actionable.actionable_for_approval is True
    assert actionable.entry_intent_status == "proposed"
    assert watching.actionable_for_approval is False
    assert watching.entry_intent_status == "watching"
    assert rejected.entry_intent_status == "rejected"

