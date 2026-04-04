from __future__ import annotations

from data.nifty50_loader import Nifty50Loader


class OptionsDataTool:
    def __init__(self, nifty50_loader: Nifty50Loader | None = None) -> None:
        self.nifty50_loader = nifty50_loader or Nifty50Loader()

    def is_eligible(self, ticker: str) -> bool:
        return ticker in set(self.nifty50_loader.load())

    def get_options_data(self, ticker: str) -> dict[str, object]:
        if not self.is_eligible(ticker):
            return {
                "ticker": ticker,
                "eligible": False,
                "reason": "not_in_nifty50_universe",
                "source": "not_applicable",
            }
        return {
            "ticker": ticker,
            "eligible": True,
            "pcr": None,
            "max_pain": None,
            "atm_iv": None,
            "iv_percentile": None,
            "india_vix": None,
            "source": "unavailable",
        }
