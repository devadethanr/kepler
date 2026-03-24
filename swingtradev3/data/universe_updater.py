from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from swingtradev3.data.nifty50_loader import Nifty50Loader
from swingtradev3.data.nifty200_loader import Nifty200Loader


OFFICIAL_INDEX_PAGES = {
    "nifty50": "https://www.niftyindices.com/indices/equity/broad-based-indices/nifty--50",
    "nifty200": "https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-200",
}


class UniverseUpdater:
    def __init__(
        self,
        session: requests.Session | None = None,
        nifty50_loader: Nifty50Loader | None = None,
        nifty200_loader: Nifty200Loader | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
                )
            }
        )
        self.nifty50_loader = nifty50_loader or Nifty50Loader()
        self.nifty200_loader = nifty200_loader or Nifty200Loader()

    @staticmethod
    def _extract_constituent_url(html: str, base_url: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            text = " ".join(link.stripped_strings).strip().lower()
            href = link.get("href", "")
            if "index constituent" in text or href.lower().endswith(".csv"):
                return urljoin(base_url, href)
        raise RuntimeError(f"Could not find index constituent download link on {base_url}")

    @staticmethod
    def _parse_constituent_csv(payload: str) -> list[dict[str, str]]:
        reader = csv.DictReader(io.StringIO(payload))
        entries: list[dict[str, str]] = []
        for row in reader:
            symbol = (
                row.get("Symbol")
                or row.get("SYMBOL")
                or row.get("symbol")
                or row.get("Ticker")
                or row.get("ticker")
            )
            name = (
                row.get("Company Name")
                or row.get("Company")
                or row.get("company_name")
                or row.get("Name")
                or row.get("name")
            )
            if not symbol:
                continue
            ticker = str(symbol).strip().upper()
            if not ticker:
                continue
            entries.append({"ticker": ticker, "name": str(name or ticker).strip() or ticker})
        if not entries:
            raise RuntimeError("Index constituent CSV contained no ticker rows")
        return entries

    def _fetch_constituents(self, index_key: str) -> list[dict[str, str]]:
        if index_key not in OFFICIAL_INDEX_PAGES:
            raise KeyError(f"Unsupported index key: {index_key}")
        page_url = OFFICIAL_INDEX_PAGES[index_key]
        page_response = self.session.get(page_url, timeout=30)
        page_response.raise_for_status()
        constituent_url = self._extract_constituent_url(page_response.text, page_url)
        csv_response = self.session.get(constituent_url, timeout=30)
        csv_response.raise_for_status()
        return self._parse_constituent_csv(csv_response.text)

    def refresh_nifty50(self) -> list[dict[str, str]]:
        entries = self._fetch_constituents("nifty50")
        self.nifty50_loader.store(entries)
        return entries

    def refresh_nifty200(self) -> list[dict[str, str]]:
        entries = self._fetch_constituents("nifty200")
        self.nifty200_loader.store(entries)
        return entries

    def refresh_all(self) -> dict[str, int]:
        nifty50 = self.refresh_nifty50()
        nifty200 = self.refresh_nifty200()
        return {"nifty50": len(nifty50), "nifty200": len(nifty200)}


def refresh_universes() -> dict[str, int]:
    return UniverseUpdater().refresh_all()


if __name__ == "__main__":
    print(refresh_universes())
