from __future__ import annotations

from swingtradev3.config import cfg
from swingtradev3.models import GTTOrder
from swingtradev3.paper.gtt_simulator import GTTSimulator


class GTTManager:
    def __init__(self, simulator: GTTSimulator | None = None) -> None:
        self.simulator = simulator or GTTSimulator()

    def place_gtt(self, position_id: str, ticker: str, stop_price: float, target_price: float) -> GTTOrder:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Live GTT placement requires Kite credentials")
        return self.simulator.place(position_id, ticker, stop_price, target_price)

    def modify_gtt(self, position_id: str, new_trigger: float) -> GTTOrder:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Live GTT modification requires Kite credentials")
        return self.simulator.modify_stop(position_id, new_trigger)

    def cancel_gtt(self, position_id: str) -> None:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Live GTT cancellation requires Kite credentials")
        self.simulator.cancel(position_id)

    def get_gtt(self, position_id: str) -> GTTOrder | None:
        return self.simulator.get(position_id)
