from __future__ import annotations


class OptionsDataTool:
    def get_options_data(self, ticker: str) -> dict[str, object]:
        return {
            "ticker": ticker,
            "pcr": None,
            "max_pain": None,
            "atm_iv": None,
            "iv_percentile": None,
            "india_vix": None,
            "source": "unavailable",
        }
