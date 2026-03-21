from swingtradev3.tools.execution.gtt_manager import GTTManager


def test_gtt_manager_exposes_simulator_in_non_live_mode() -> None:
    manager = GTTManager()
    order = manager.place_gtt("pos-1", "SBIN", 700.0, 760.0)
    assert order.position_id == "pos-1"
