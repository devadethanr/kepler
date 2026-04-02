from __future__ import annotations

import os
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from swingtradev3.backtest.data_fetcher import BacktestDataFetcher
from swingtradev3.config import cfg
from swingtradev3.models import (
    AccountState,
    EntryZone,
    PositionState,
    ResearchDecision,
    TradeRecord,
)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "close" not in df.columns:
        return df

    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df["open"] = pd.to_numeric(df["open"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi_14"] = 100 - (100 / (1 + rs))

    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()

    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df["atr_14"] = true_range.rolling(14).mean()

    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

    return df

    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df["open"] = pd.to_numeric(df["open"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    df["rsi_14"] = ta.rsi(df["close"], length=14)
    df["ema_50"] = ta.ema(df["close"], length=50)
    df["ema_200"] = ta.ema(df["close"], length=200)
    df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

    return df


@dataclass
class BacktestState:
    cash: float
    positions: dict[str, PositionState] = field(default_factory=dict)
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BacktestResult:
    trades: list[TradeRecord]
    equity_curve: list[dict[str, Any]]
    final_capital: float
    metrics: dict[str, float]


class BacktestEngine:
    def __init__(
        self,
        data_fetcher: BacktestDataFetcher | None = None,
    ) -> None:
        self.data_fetcher = data_fetcher or BacktestDataFetcher()
        self.slippage_pct = cfg.backtest.slippage_pct
        self.brokerage = cfg.backtest.brokerage_per_order

    def _apply_slippage(self, price: float, side: str) -> float:
        if side.lower() == "buy":
            return price * (1 + self.slippage_pct)
        return price * (1 - self.slippage_pct)

    def _get_fill_price(self, df: pd.DataFrame, day_idx: int, side: str) -> float:
        fill_price_cfg = cfg.backtest.fill_price

        if fill_price_cfg == "next_open" and day_idx + 1 < len(df):
            return self._apply_slippage(df.iloc[day_idx + 1]["close"], side)
        elif fill_price_cfg == "close":
            return self._apply_slippage(df.iloc[day_idx]["close"], side)
        return self._apply_slippage(df.iloc[day_idx]["close"], side)

    def _check_signals(self, df: pd.DataFrame, day_idx: int) -> list[ResearchDecision]:
        signals = []

        if day_idx < 60:
            return signals

        row = df.iloc[day_idx]
        prev_row = df.iloc[day_idx - 1]

        rsi = row.get("rsi_14")
        ema_50 = row.get("ema_50")
        ema_200 = row.get("ema_200")
        close = row["close"]
        volume = row.get("volume", 0)
        volume_ratio = row.get("volume_ratio", 1)

        if rsi and ema_50 and ema_200:
            bullish = (
                ema_50 > ema_200
                and close > ema_50
                and rsi > 40
                and volume > 0
                and volume_ratio > 0.8
            )

            if bullish:
                stop = close * 0.97
                target = close * 1.08
                signals.append(
                    ResearchDecision(
                        ticker=df.name,
                        score=7.5,
                        setup_type="breakout",
                        entry_zone=EntryZone(low=close * 0.99, high=close * 1.01),
                        stop_price=stop,
                        target_price=target,
                        holding_days_expected=10,
                        confidence_reasoning="Bullish: EMA trend + RSI confirm",
                        risk_flags=[],
                        sector="Unknown",
                        research_date=date.today(),
                        skill_version="backtest",
                        current_price=close,
                    )
                )

        return signals

    def _run_day(
        self,
        state: BacktestState,
        all_data: dict[str, pd.DataFrame],
        current_date: date,
        date_idx: int,
    ) -> None:
        for ticker, df in all_data.items():
            if ticker not in state.positions:
                signals = self._check_signals(df, date_idx)
                for signal in signals:
                    self._enter_position(state, signal, df, date_idx, current_date)
            else:
                self._check_exit(state, ticker, df, date_idx)

        total_equity = state.cash + sum(
            pos.current_price * pos.quantity for pos in state.positions.values()
        )
        state.equity_curve.append(
            {
                "date": current_date.isoformat(),
                "cash": state.cash,
                "equity": total_equity,
                "positions": len(state.positions),
            }
        )

    def _enter_position(
        self,
        state: BacktestState,
        signal: ResearchDecision,
        df: pd.DataFrame,
        day_idx: int,
        current_date: date,
    ) -> None:
        if signal.ticker in state.positions:
            return

        available_capital = state.cash * (1 - cfg.trading.min_cash_reserve_pct)
        position_size = int((available_capital * 0.25) / signal.entry_zone.high)

        if position_size <= 0:
            return

        entry_price = self._get_fill_price(df, day_idx, "buy")

        state.cash -= entry_price * position_size
        state.positions[signal.ticker] = PositionState(
            ticker=signal.ticker,
            quantity=position_size,
            entry_price=entry_price,
            current_price=entry_price,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            opened_at=datetime.now(),
            entry_order_id=f"BT-{day_idx}",
            stop_gtt_id=f"BT-STOP-{day_idx}",
            target_gtt_id=f"BT-TGT-{day_idx}",
            thesis_score=signal.score,
            research_date=current_date,
            skill_version=signal.skill_version,
            sector=signal.sector,
        )

    def _check_exit(
        self,
        state: BacktestState,
        ticker: str,
        df: pd.DataFrame,
        day_idx: int,
    ) -> None:
        position = state.positions[ticker]
        current_price = df.iloc[day_idx]["close"]
        position.current_price = current_price

        exited = False
        exit_reason = ""
        exit_price = 0.0

        if current_price <= position.stop_price:
            exit_price = self._get_fill_price(df, day_idx, "sell")
            exit_reason = "stop"
            exited = True
        elif current_price >= position.target_price:
            exit_price = self._get_fill_price(df, day_idx, "sell")
            exit_reason = "target"
            exited = True

        if exited and exit_price > 0:
            pnl = (exit_price - position.entry_price) * position.quantity

            trade = TradeRecord(
                trade_id=f"TRD-{len(state.trades)}",
                ticker=ticker,
                quantity=position.quantity,
                entry_price=position.entry_price,
                exit_price=exit_price,
                pnl_abs=pnl,
                pnl_pct=(exit_price / position.entry_price - 1) * 100,
                exit_reason=exit_reason,
                opened_at=position.opened_at,
                closed_at=datetime.now(),
                research_date=position.research_date,
                skill_version=position.skill_version,
            )
            state.trades.append(trade)
            state.cash += exit_price * position.quantity
            del state.positions[ticker]

    def run(
        self,
        tickers: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> BacktestResult:
        start = start_date or cfg.backtest.start_date
        end = end_date or cfg.backtest.end_date

        state = BacktestState(cash=cfg.backtest.initial_capital)

        all_data: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            df = self.data_fetcher.fetch(ticker)
            if not df.empty:
                df = df.sort_values("date")
                df = df[(df["date"] >= start) & (df["date"] <= end)]
                df = add_indicators(df)
                df.name = ticker
                all_data[ticker] = df

        if not all_data:
            return BacktestResult([], [], state.cash, {})

        min_dates = [df["date"].min() for df in all_data.values()]
        max_dates = [df["date"].max() for df in all_data.values()]

        common_start = max(min_dates)
        common_end = min(max_dates)

        dates = pd.date_range(common_start, common_end, freq="D")
        trading_dates = [d for d in dates if d.weekday() < 5]

        for current_date in trading_dates:
            for ticker, df in all_data.items():
                date_masks = df["date"] == current_date
                if date_masks.sum() == 0:
                    continue

                date_idx = df.index[date_masks][0]
                self._run_day(state, all_data, current_date.date(), date_idx)

        for ticker, position in state.positions.items():
            df = all_data.get(ticker)
            if df is not None and not df.empty:
                last_price = df.iloc[-1]["close"]
                exit_price = self._apply_slippage(last_price, "sell")
                pnl = (exit_price - position.entry_price) * position.quantity

                trade = TradeRecord(
                    trade_id=f"TRD-{len(state.trades)}",
                    ticker=ticker,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    pnl_abs=pnl,
                    pnl_pct=(exit_price / position.entry_price - 1) * 100,
                    exit_reason="end_of_backtest",
                    opened_at=position.opened_at,
                    closed_at=datetime.now(),
                    research_date=position.research_date,
                    skill_version=position.skill_version,
                )
                state.trades.append(trade)
                state.cash += exit_price * position.quantity

        final_capital = state.cash

        return BacktestResult(
            trades=state.trades,
            equity_curve=state.equity_curve,
            final_capital=final_capital,
            metrics=self._calculate_metrics(state),
        )

    def _calculate_metrics(self, state: BacktestState) -> dict[str, float]:
        if not state.trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
            }

        wins = [t.pnl_abs for t in state.trades if t.pnl_abs > 0]
        losses = [abs(t.pnl_abs) for t in state.trades if t.pnl_abs < 0]

        win_rate = len(wins) / len(state.trades) if state.trades else 0
        profit_factor = sum(wins) / sum(losses) if losses else 0

        total_return = (
            (state.equity_curve[-1]["equity"] / cfg.backtest.initial_capital - 1)
            if state.equity_curve
            else 0
        )

        equity = [e["equity"] for e in state.equity_curve]
        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        returns = []
        for i in range(1, len(equity)):
            if equity[i - 1] > 0:
                returns.append((equity[i] - equity[i - 1]) / equity[i - 1])

        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = (
            (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            if returns
            else 1
        )
        sharpe = (avg_return / std_return * (252**0.5)) if std_return > 0 else 0

        return {
            "total_trades": len(state.trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_return": total_return,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,
        }
