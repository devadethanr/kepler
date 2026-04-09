from swingtradev3.paper.gtt_simulator import GTTSimulator


def test_modify_gtt_stop() -> None:
    simulator = GTTSimulator()
    order = simulator.place("pos-1", "RELIANCE", 1400.0, 1500.0)
    assert order.stop_price == 1400.0
    updated = simulator.modify_stop("pos-1", 1415.0)
    assert updated.stop_price == 1415.0
