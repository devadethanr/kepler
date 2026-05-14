from __future__ import annotations

from execution.operator_controls import (
    clear_block_new_entries,
    is_block_new_entries_active,
    read_block_new_entries,
    set_block_new_entries,
)


def test_block_new_entries_keeps_independent_reasons_until_each_is_cleared():
    set_block_new_entries(reason="stream_unavailable", source="test_phase9")
    set_block_new_entries(reason="gtt_rejected", source="test_phase9")

    block = read_block_new_entries() or {}
    assert block["blocked"] is True
    assert block["active_reasons"] == ["gtt_rejected", "stream_unavailable"]

    clear_block_new_entries(reason="stream_unavailable", source="test_phase9")

    block = read_block_new_entries() or {}
    assert block["blocked"] is True
    assert block["active_reasons"] == ["gtt_rejected"]
    assert is_block_new_entries_active() is True

    clear_block_new_entries(reason="gtt_rejected", source="test_phase9")

    block = read_block_new_entries() or {}
    assert block["blocked"] is False
    assert block["active_reasons"] == []
