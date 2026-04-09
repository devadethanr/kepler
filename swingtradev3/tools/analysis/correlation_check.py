"""
Correlation Check Tool
======================
Checks pairwise correlation between open positions.
Computes portfolio beta, VaR, and correlation matrix.
Pure computation — no decisions.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def check_correlation(
    positions: list[str],
    returns_data: dict[str, pd.Series] | None = None,
    benchmark_returns: pd.Series | None = None,
) -> dict[str, Any]:
    """
    Check correlation between open positions.

    Args:
        positions: List of ticker symbols
        returns_data: Dict of {ticker: daily_returns_series}
        benchmark_returns: Daily returns of benchmark (Nifty 50)

    Returns:
        {
            correlation_matrix: dict,
            max_correlation: float,
            max_correlation_pair: tuple,
            portfolio_beta: float | None,
            portfolio_var_95: float | None,
            warning: bool,
        }
    """
    if returns_data is None or len(returns_data) < 2:
        return {
            "correlation_matrix": {},
            "max_correlation": None,
            "max_correlation_pair": None,
            "portfolio_beta": None,
            "portfolio_var_95": None,
            "warning": False,
            "message": "Need at least 2 positions with returns data",
        }

    # Build returns DataFrame
    tickers = [t for t in positions if t in returns_data]
    if len(tickers) < 2:
        return {
            "correlation_matrix": {},
            "max_correlation": None,
            "max_correlation_pair": None,
            "portfolio_beta": None,
            "portfolio_var_95": None,
            "warning": False,
            "message": "Insufficient returns data",
        }

    df = pd.DataFrame({t: returns_data[t] for t in tickers})
    df = df.dropna()

    if len(df) < 20:
        return {
            "correlation_matrix": {},
            "max_correlation": None,
            "max_correlation_pair": None,
            "portfolio_beta": None,
            "portfolio_var_95": None,
            "warning": False,
            "message": "Insufficient data points (need >= 20)",
        }

    # Correlation matrix
    corr_matrix = df.corr()

    # Find max pairwise correlation (excluding diagonal)
    max_corr = 0.0
    max_pair = None
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            corr = abs(corr_matrix.iloc[i, j])
            if corr > max_corr:
                max_corr = corr
                max_pair = (tickers[i], tickers[j])

    # Portfolio beta (if benchmark provided)
    portfolio_beta = None
    if benchmark_returns is not None:
        aligned = pd.DataFrame({
            "portfolio": df.mean(axis=1),
            "benchmark": benchmark_returns,
        }).dropna()
        if len(aligned) >= 20:
            cov = aligned["portfolio"].cov(aligned["benchmark"])
            var = aligned["benchmark"].var()
            if var > 0:
                portfolio_beta = round(cov / var, 3)

    # Portfolio VaR (95% confidence)
    portfolio_returns = df.mean(axis=1)
    portfolio_var_95 = round(float(np.percentile(portfolio_returns, 5)), 4)

    # Warning if any pair > 0.7
    warning = max_corr > 0.7

    return {
        "correlation_matrix": corr_matrix.round(3).to_dict(),
        "max_correlation": round(max_corr, 3),
        "max_correlation_pair": max_pair,
        "portfolio_beta": portfolio_beta,
        "portfolio_var_95": portfolio_var_95,
        "warning": warning,
        "message": "High correlation detected" if warning else "Correlation within acceptable range",
        "data_points": len(df),
    }
