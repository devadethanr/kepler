from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class FiiDiiDataTool:
    REPORT_URL = "https://www.nseindia.com/reports/fii-dii"

    def __init__(self, cache_path: Path | None = None, ttl_hours: int = 12) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "fii_dii_cache.json")
        self.ttl_hours = ttl_hours
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
                )
            }
        )

    def _cached(self) -> dict[str, object] | None:
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

    def _store(self, payload: dict[str, object]) -> dict[str, object]:
        write_json(self.cache_path, {"fetched_at": datetime.utcnow().isoformat(), "data": payload})
        return payload

    @staticmethod
    def _extract_csv_url(html: str, base_url: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = " ".join(link.stripped_strings).lower()
            if href.lower().endswith(".csv") or ("csv" in text and "fii" in text and "dii" in text):
                return urljoin(base_url, href)
        raise RuntimeError("Could not find NSE FII/DII CSV download link")

    @staticmethod
    def _parse_csv(payload: str) -> dict[str, object]:
        reader = csv.DictReader(io.StringIO(payload))
        rows: list[dict[str, object]] = []
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
            net_value = float(str(row.get("Net Value") or row.get("Net") or (buy_value - sell_value)).replace(",", "") or 0)
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
            "sector_flows": {},
            "rows": rows,
            "source": "nse",
        }

    def get_fii_dii(self) -> dict[str, object]:
        cached = self._cached()
        if cached is not None:
            return cached
        try:
            page = self.session.get(self.REPORT_URL, timeout=30)
            page.raise_for_status()
            csv_url = self._extract_csv_url(page.text, self.REPORT_URL)
            csv_response = self.session.get(csv_url, timeout=30)
            csv_response.raise_for_status()
            return self._store(self._parse_csv(csv_response.text))
        except Exception:
            fallback = read_json(self.cache_path, {}).get("data")
            if fallback:
                fallback["source"] = "cache"
                return fallback
            return {
                "date": date.today().isoformat(),
                "fii_net_crore": None,
                "dii_net_crore": None,
                "sector_flows": {},
                "rows": [],
                "source": "not_configured",
            }
