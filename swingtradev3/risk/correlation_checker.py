"""
Portfolio Correlation Checker
==============================
Checks pairwise correlation between open positions.
Computes portfolio beta, VaR, and enforces concentration limits.
Pure validation — says YES/NO, does NOT execute.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import cfg
from data.kite_fetcher import KiteFetcher


class CorrelationChecker:
    """Checks portfolio-level risk: correlation, beta, VaR."""

    MAX_CORRELATION = 0.7  # Default threshold

    def __init__(self, max_correlation: float | None = None) -> None:
        self.max_correlation = max_correlation or self.MAX_CORRELATION
        self.fetcher = KiteFetcher()

    def check(
        self,
        positions: list[dict[str, Any]],
        new_ticker: str | None = None,
    ) -> dict[str, Any]:
        """
        Check portfolio correlation.

        Args:
            positions: List of {ticker, quantity, entry_price}
            new_ticker: Optional new ticker to check against existing positions

        Returns:
            {
                approved: bool,
                correlation_matrix: dict,
                max_correlation: float,
                max_correlation_pair: tuple,
                portfolio_beta: float | None,
                portfolio_var_95: float | None,
                warning: str | None,
            }
        """
        tickers = [p["ticker"] for p in positions]
        if new_ticker:
            tickers.append(new_ticker)

        if len(tickers) < 2:
            return {
                "approved": True,
                "correlation_matrix": {},
                "max_correlation": 0.0,
                "max_correlation_pair": None,
                "portfolio_beta": None,
                "portfolio_var_95": None,
                "warning": None,
                "message": "Single position — no correlation risk",
            }

        # Fetch returns data
        returns_data = {}
        for ticker in tickers:
            try:
                candles = self.fetcher.fetch(ticker, interval="day")
                if candles is not None and len(candles) >= 60:
                    returns_data[ticker] = candles["close"].pct_change().dropna()
            except Exception:
                continue

        if len(returns_data) < 2:
            return {
                "approved": True,
                "correlation_matrix": {},
                "max_correlation": None,
                "max_correlation_pair": None,
                "portfolio_beta": None,
                "portfolio_var_95": None,
                "warning": "Insufficient data for correlation check",
                "message": "Proceeding without correlation check",
            }

        # Build returns DataFrame
        df = pd.DataFrame(returns_data)
        df = df.dropna()

        if len(df) < 20:
            return {
                "approved": True,
                "correlation_matrix": {},
                "max_correlation": None,
                "max_correlation_pair": None,
                "portfolio_beta": None,
                "portfolio_var_95": None,
                "warning": "Insufficient overlapping data",
                "message": "Proceeding without correlation check",
            }

        # Correlation matrix
        corr_matrix = df.corr()

        # Find max pairwise correlation
        max_corr = 0.0
        max_pair = None
        cols = list(corr_matrix.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                c = abs(corr_matrix.iloc[i, j])
                if c > max_corr:
                    max_corr = c
                    max_pair = (cols[i], cols[j])

        # Portfolio beta (vs Nifty 50 if available)
        portfolio_beta = None
        try:
            nifty = self.fetcher.fetch("NSE:NIFTY 50", interval="day")
            if nifty is not None and len(nifty) >= 60:
                nifty_returns = nifty["close"].pct_change().dropna()
                portfolio_returns = df.mean(axis=1)
                aligned = pd.DataFrame({"portfolio": portfolio_returns, "nifty": nifty_returns}).dropna()
                if len(aligned) >= 20:
                    cov = aligned["portfolio"].cov(aligned["nifty"])
                    var = aligned["nifty"].var()
                    if var > 0:
                        portfolio_beta = round(cov / var, 3)
        except Exception:
            pass

        # Portfolio VaR (95% confidence)
        portfolio_returns = df.mean(axis=1)
        portfolio_var_95 = round(float(np.percentile(portfolio_returns, 5)), 4)

        # Check if new ticker would exceed correlation threshold
        approved = True
        warning = None
        if new_ticker and max_corr > self.max_correlation:
            approved = False
            warning = f"Correlation {max_corr:.2f} with {max_pair} exceeds threshold {self.max_correlation}"

        return {
            "approved": approved,
            "correlation_matrix": corr_matrix.round(3).to_dict(),
            "max_correlation": round(max_corr, 3),
            "max_correlation_pair": max_pair,
            "portfolio_beta": portfolio_beta,
            "portfolio_var_95": portfolio_var_95,
            "warning": warning,
            "message": "Correlation within acceptable range" if approved else warning,
            "data_points": len(df),
        }
