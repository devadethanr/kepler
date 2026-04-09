from swingtradev3.paper.fill_engine import FillEngine
from swingtradev3.paper.gtt_simulator import GTTSimulator


def test_fill_engine_applies_slippage() -> None:
    fill = FillEngine().fill("INFY", "buy", 10, 100.0, "ord-1")
    assert fill.status == "filled"
    assert fill.average_price > 100.0


def test_gtt_simulator_triggers_stop() -> None:
    simulator = GTTSimulator()
    simulator.place("pos-1", "INFY", 95.0, 110.0)
    result = simulator.process_candle("pos-1", candle_low=94.0, candle_high=99.0)
    assert result is not None
    assert result.exit_reason == "stop_loss"
