"""
Institutional Flows Tracker
============================
Tracks FII/DII flows, block deals, and bulk deals from NSE.
Pure data fetching — no analysis, no decisions.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from paths import CONTEXT_DIR
from storage import read_json, write_json


class InstitutionalFlowsTool:
    """Fetches FII/DII flows, block deals, and bulk deals."""

    FII_DII_URL = "https://www.nseindia.com/reports/fii-dii"
    BLOCK_DEALS_URL = "https://www.nseindia.com/market-data/block-deals"
    BULK_DEALS_URL = "https://www.nseindia.com/market-data/bulk-deals"

    def __init__(self, cache_path: Path | None = None, ttl_hours: int = 12) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "institutional_flows_cache.json")
        self.ttl_hours = ttl_hours
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def _cached(self) -> dict[str, Any] | None:
        payload = read_json(self.cache_path, {})
        fetched_at = payload.get("fetched_at")
        if not fetched_at:
            return None
        try:
            age = datetime.utcnow() - datetime.fromisoformat(str(fetched_at))
        except ValueError:
            return None
        if age > timedelta(hours=self.ttl_hours):
            return None
        return payload.get("data")

    def _store(self, payload: dict[str, Any]) -> dict[str, Any]:
        write_json(self.cache_path, {"fetched_at": datetime.utcnow().isoformat(), "data": payload})
        return payload

    def _extract_csv_url(self, html: str, base_url: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = " ".join(link.stripped_strings).lower()
            if href.lower().endswith(".csv") or ("csv" in text and "fii" in text):
                return urljoin(base_url, href)
        raise RuntimeError("Could not find NSE FII/DII CSV download link")

    def _parse_fii_dii_csv(self, payload: str) -> dict[str, Any]:
        reader = csv.DictReader(io.StringIO(payload))
        rows: list[dict[str, Any]] = []
        fii_net = None
        dii_net = None
        report_date = date.today().isoformat()

        for row in reader:
            category = str(
                row.get("Category")
                or row.get("Client Type")
                or row.get("category")
                or row.get("client type")
                or ""
            ).strip()
            if not category:
                continue
            buy_value = float(str(row.get("Buy Value") or row.get("Buy") or 0).replace(",", "") or 0)
            sell_value = float(str(row.get("Sell Value") or row.get("Sell") or 0).replace(",", "") or 0)
            net_value = float(
                str(row.get("Net Value") or row.get("Net") or (buy_value - sell_value)).replace(",", "") or 0
            )
            rows.append(
                {
                    "category": category,
                    "buy_value_cr": buy_value,
                    "sell_value_cr": sell_value,
                    "net_value_cr": net_value,
                }
            )
            lower = category.lower()
            if "fii" in lower or "fpi" in lower:
                fii_net = net_value
            if "dii" in lower:
                dii_net = net_value
            raw_date = row.get("Date") or row.get("date")
            if raw_date:
                report_date = str(raw_date)

        return {
            "date": report_date,
            "fii_net_crore": fii_net,
            "dii_net_crore": dii_net,
            "total_net_crore": (fii_net or 0) + (dii_net or 0),
            "rows": rows,
            "source": "nse",
        }

    def get_fii_dii(self) -> dict[str, Any]:
        """Fetch FII/DII daily flow data."""
        cached = self._cached()
        if cached is not None and cached.get("fii_dii"):
            return cached.get("fii_dii", {})

        try:
            page = self.session.get(self.FII_DII_URL, timeout=30)
            page.raise_for_status()
            csv_url = self._extract_csv_url(page.text, self.FII_DII_URL)
            csv_response = self.session.get(csv_url, timeout=30)
            csv_response.raise_for_status()
            result = self._parse_fii_dii_csv(csv_response.text)
        except Exception:
            fallback = read_json(self.cache_path, {}).get("data", {}).get("fii_dii")
            if fallback:
                fallback["source"] = "cache"
                return fallback
            return {
                "date": date.today().isoformat(),
                "fii_net_crore": None,
                "dii_net_crore": None,
                "total_net_crore": None,
                "rows": [],
                "source": "not_configured",
            }

        # Update cache with new data
        full_cache = read_json(self.cache_path, {})
        full_cache.setdefault("data", {})["fii_dii"] = result
        full_cache["fetched_at"] = datetime.utcnow().isoformat()
        write_json(self.cache_path, full_cache)

        return result

    def get_block_deals(self) -> list[dict[str, Any]]:
        """Fetch today's block deals."""
        cached = read_json(self.cache_path, {}).get("data", {}).get("block_deals")
        if cached:
            cached_date = cached.get("date")
            if cached_date == date.today().isoformat():
                return cached.get("deals", [])

        # Block deals require JS rendering — return empty for now
        # In production, would use Selenium or NSE API directly
        return []

    def get_bulk_deals(self) -> list[dict[str, Any]]:
        """Fetch today's bulk deals."""
        cached = read_json(self.cache_path, {}).get("data", {}).get("bulk_deals")
        if cached:
            cached_date = cached.get("date")
            if cached_date == date.today().isoformat():
                return cached.get("deals", [])

        return []

    def get_all(self) -> dict[str, Any]:
        """Get all institutional flow data."""
        fii_dii = self.get_fii_dii()
        block_deals = self.get_block_deals()
        bulk_deals = self.get_bulk_deals()

        result = {
            "date": date.today().isoformat(),
            "fii_dii": fii_dii,
            "block_deals": block_deals,
            "bulk_deals": bulk_deals,
            "source": fii_dii.get("source", "not_configured"),
        }

        # Update full cache
        full_cache = read_json(self.cache_path, {})
        full_cache["data"] = result
        full_cache["fetched_at"] = datetime.utcnow().isoformat()
        write_json(self.cache_path, full_cache)

        return result
