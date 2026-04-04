from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from swingtradev3.config import cfg
from swingtradev3.paper.slippage_model import apply_slippage


@dataclass
class FillResult:
    order_id: str
    status: str
    average_price: float
    quantity: int
    brokerage: float
    net_pnl: float = 0.0
    filled_at: datetime | None = None


class FillEngine:
    def fill(
        self,
        ticker: str,
        side: str,
        quantity: int,
        reference_price: float,
        order_id: str,
        brokerage: float | None = None,
    ) -> FillResult:
        price = apply_slippage(reference_price, side)
        return FillResult(
            order_id=order_id,
            status="filled",
            average_price=price,
            quantity=quantity,
            brokerage=cfg.backtest.brokerage_per_order if brokerage is None else brokerage,
            filled_at=datetime.utcnow(),
        )
