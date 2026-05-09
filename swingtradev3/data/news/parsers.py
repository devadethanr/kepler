from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urljoin


CATALYST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "earnings": ("earnings", "results", "profit", "revenue", "ebitda", "quarter"),
    "order_win": ("order", "contract", "deal", "award", "project", "partnership"),
    "regulation": ("sebi", "rbi", "regulator", "penalty", "fine", "ban", "probe"),
    "corporate_action": ("dividend", "split", "bonus", "rights", "buyback", "merger"),
    "management": ("ceo", "cfo", "resign", "appoint", "board", "promoter"),
    "broker_note": ("target price", "upgrade", "downgrade", "buy", "sell", "reduce"),
    "ipo": ("ipo", "listing", "gmp", "anchor investor"),
    "macro": ("inflation", "gdp", "policy", "budget", "crude", "currency"),
}

GENERIC_LINK_BLOCKLIST = {
    "#",
    "/",
    "javascript:void(0)",
    "javascript:;",
}


def clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<(script|style).*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_epoch_ms(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return str(value)
    if raw > 10_000_000_000:
        raw = raw / 1000
    return datetime.fromtimestamp(raw, tz=timezone.utc).isoformat()


def infer_category(*parts: Any) -> str:
    text = " ".join(clean_text(part).lower() for part in parts if part)
    for category, keywords in CATALYST_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "unknown"


def extract_tickers_from_text(
    text: str,
    universe_entries: list[dict[str, str]],
) -> list[str]:
    normalized = re.sub(r"\s+", " ", clean_text(text).upper())
    tickers: list[str] = []
    for entry in universe_entries:
        ticker = str(entry.get("ticker") or "").upper()
        name = str(entry.get("name") or ticker).upper()
        if not ticker:
            continue
        aliases = {ticker}
        cleaned_name = re.sub(
            r"\b(LTD|LIMITED|INDIA|CO|COMPANY|CORP|CORPORATION|PVT|PRIVATE)\b",
            " ",
            name,
        )
        words = [word for word in re.split(r"[^A-Z0-9&]+", cleaned_name) if len(word) >= 3]
        if words:
            aliases.add(words[0])
        if len(words) >= 2:
            aliases.add(" ".join(words[:2]))
        for alias in aliases:
            if len(alias) < 3:
                continue
            if re.search(rf"(?<![A-Z0-9]){re.escape(alias)}(?![A-Z0-9])", normalized):
                tickers.append(ticker)
                break
    return sorted(set(tickers))


def _coerce_json_payload(value: str) -> Any | None:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return json.loads(value.replace("\\/", "/"))
        except json.JSONDecodeError:
            return None


def _balanced_json_after(text: str, marker: str) -> str | None:
    index = text.find(marker)
    if index < 0:
        return None
    start = -1
    for pos in range(index + len(marker), len(text)):
        if text[pos] in "[{":
            start = pos
            break
    if start < 0:
        return None
    opener = text[start]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string = False
    escape = False
    for pos in range(start, len(text)):
        char = text[pos]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start : pos + 1]
    return None


def parse_upstox_news(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return []
    rows: list[dict[str, Any]] = []
    for instrument_key, items in data.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            title = clean_text(item.get("heading"))
            url = str(item.get("article_link") or "").strip()
            if not title and not url:
                continue
            rows.append(
                {
                    "title": title or url,
                    "summary": clean_text(item.get("summary")),
                    "url": url,
                    "published_at": parse_epoch_ms(item.get("published_time")),
                    "source_id": f"{instrument_key}:{url or title}",
                    "instrument_key": instrument_key,
                    "thumbnail": item.get("thumbnail"),
                    "category": infer_category(title, item.get("summary")),
                }
            )
    return rows


def parse_bse_announcements(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    table = (
        payload.get("Table")
        or payload.get("Table1")
        or payload.get("data")
        or payload.get("results")
        or []
    )
    if isinstance(table, dict):
        table = list(table.values())
    if not isinstance(table, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in table:
        if not isinstance(item, dict):
            continue
        title = clean_text(
            item.get("NEWS_SUB")
            or item.get("HEADLINE")
            or item.get("NEWSSUB")
            or item.get("SLONGNAME")
        )
        attachment = str(item.get("ATTACHMENTNAME") or item.get("NSURL") or "").strip()
        if attachment and not attachment.startswith(("http://", "https://")):
            attachment = f"https://www.bseindia.com/xml-data/corpfiling/AttachLive/{attachment}"
        url = attachment or str(item.get("URL") or "").strip()
        company = clean_text(item.get("SLONGNAME") or item.get("LONG_NAME") or "")
        summary = clean_text(item.get("MORE") or item.get("NEWS_BODY") or item.get("HEADLINE"))
        if not title and not url:
            continue
        rows.append(
            {
                "title": title or url,
                "summary": summary,
                "url": url,
                "published_at": item.get("DissemDT")
                or item.get("DT_TM")
                or item.get("NEWS_DT")
                or item.get("Date"),
                "source_id": str(item.get("NEWSID") or item.get("SCRIP_CD") or url or title),
                "company_names": [company] if company else [],
                "category": infer_category(title, summary),
            }
        )
    return rows


def parse_groww_newsdata(html: str, base_url: str = "https://groww.in") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    payloads = []
    for marker in ('"newsData"', "newsData", '"news"', '"marketNews"'):
        raw = _balanced_json_after(html, marker)
        if raw:
            decoded = _coerce_json_payload(raw)
            if decoded is not None:
                payloads.append(decoded)
    for payload in payloads:
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("news")
        else:
            items = []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            title = clean_text(item.get("title") or item.get("heading"))
            url = str(
                item.get("url")
                or item.get("newsUrl")
                or item.get("articleUrl")
                or ""
            ).strip()
            if url:
                url = urljoin(base_url, url)
            if not title and not url:
                continue
            rows.append(
                {
                    "title": title or url,
                    "summary": clean_text(item.get("summary") or item.get("description")),
                    "url": url,
                    "published_at": (
                        item.get("pubDate") or item.get("publishedAt") or item.get("date")
                    ),
                    "source_id": str(item.get("id") or url or title),
                    "provider_name": clean_text(item.get("source") or item.get("publisher")),
                    "category": infer_category(title, item.get("summary")),
                }
            )
    return rows


def parse_json_ld_item_list(html: str, base_url: str) -> list[dict[str, Any]]:
    scripts = re.findall(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    rows: list[dict[str, Any]] = []
    for script in scripts:
        decoded = _coerce_json_payload(unescape(script.strip()))
        if decoded is None:
            continue
        candidates = decoded if isinstance(decoded, list) else [decoded]
        queue = [candidate for candidate in candidates if isinstance(candidate, dict)]
        while queue:
            candidate = queue.pop(0)
            if not isinstance(candidate, dict):
                continue
            graph = candidate.get("@graph")
            if isinstance(graph, list):
                queue.extend(item for item in graph if isinstance(item, dict))
            item_type = str(candidate.get("@type") or "").lower()
            if "itemlist" not in item_type:
                continue
            elements = candidate.get("itemListElement") or []
            if not isinstance(elements, list):
                continue
            for element in elements:
                item = element.get("item") if isinstance(element, dict) else element
                if isinstance(item, str):
                    title = item
                    url = item
                elif isinstance(item, dict):
                    title = clean_text(
                        item.get("name") or item.get("headline") or item.get("title")
                    )
                    url = str(item.get("url") or item.get("@id") or "").strip()
                else:
                    continue
                url = urljoin(base_url, url)
                if not title and not url:
                    continue
                rows.append(
                    {
                        "title": title or url,
                        "summary": "",
                        "url": url,
                        "published_at": None,
                        "source_id": url,
                        "category": infer_category(title),
                    }
                )
    return rows


def parse_article_links(html: str, base_url: str, *, max_items: int = 20) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    link_pattern = r"<a\s+[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>"
    for match in re.finditer(link_pattern, html, re.I | re.S):
        href = unescape(match.group(1)).strip()
        if not href or href.lower() in GENERIC_LINK_BLOCKLIST:
            continue
        text = clean_text(match.group(2))
        if len(text) < 12:
            continue
        url = urljoin(base_url, href)
        if url in seen:
            continue
        if not any(
            token in url.lower()
            for token in (
                "news",
                "market",
                "stock",
                "company",
                "article",
                "business",
                "economy",
                "results",
                "ipo",
            )
        ):
            continue
        seen.add(url)
        rows.append(
            {
                "title": text,
                "summary": "",
                "url": url,
                "published_at": None,
                "source_id": url,
                "category": infer_category(text, url),
            }
        )
        if len(rows) >= max_items:
            break
    return rows


def parse_source_specific_html(
    provider: str,
    html: str,
    base_url: str,
) -> list[dict[str, Any]]:
    if provider == "groww_crawler":
        rows = parse_groww_newsdata(html, base_url)
        if rows:
            return rows
    if provider in {
        "moneycontrol_tag_crawler",
        "moneycontrol_company_crawler",
        "etmarkets_crawler",
        "ndtvprofit_crawler",
        "cnbctv18_crawler",
        "business_standard_crawler",
        "livemint_crawler",
        "businessline_crawler",
        "financial_express_crawler",
    }:
        rows = parse_json_ld_item_list(html, base_url)
        if rows:
            return rows
    return parse_article_links(html, base_url)
