import pandas as pd

from swingtradev3.config import cfg
from swingtradev3.data.indicators import calculate_all


def _sample_candles() -> pd.DataFrame:
    rows = []
    base = 100.0
    for idx in range(300):
        close = base + idx * 0.5
        rows.append(
            {
                "date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=idx),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 500000 + idx * 10,
            }
        )
    return pd.DataFrame(rows)


def test_calculate_all_indicators() -> None:
    output = calculate_all(_sample_candles(), cfg.indicators)
    assert output["above_200ema"] is True
    assert "detected_patterns" in output
    assert output["base_weeks"] >= 0
