"""Small, host-safe primary feed parser and bounded public fetcher.

No database access, provider fallback, JavaScript, or browser profile is used.
"""

from __future__ import annotations

import hashlib
import http.client
import ipaddress
import multiprocessing
import re
import socket
import ssl
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

SOURCES = {
    "sebi_rss": ("https://www.sebi.gov.in/sebirss.xml", "regulator"),
    "rbi_press_releases_rss": ("https://rbi.org.in/pressreleases_rss.xml", "regulator"),
    "pib_rss": (
        "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3&reg=48",
        "government_release",
    ),
}
MAX_BYTES = 1_000_000
_RATE_LOCK = threading.Lock()
_LAST_REQUEST: dict[str, float] = {}
MIN_REFRESH_SECONDS = 60


def publication_date(raw: str | None) -> dict:
    """Return only a date for date-only values, even when an offset is supplied."""
    raw = (raw or "").strip()
    unknown = {
        "published_raw": raw or None,
        "published_at_utc": None,
        "published_date": None,
        "timezone_basis": None,
        "publication_precision": "unknown",
    }
    if not raw:
        return unknown
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            day = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return unknown
        return {
            **unknown,
            "published_date": day.isoformat(),
            "timezone_basis": "unknown",
            "publication_precision": "date",
        }
    match = re.fullmatch(r"(\d{1,2} [A-Za-z]{3},? \d{4})(?:\s+([+-]\d{4}))?", raw)
    if match:
        offset = match.group(2)
        if offset and (int(offset[1:3]) > 23 or int(offset[3:]) > 59):
            return unknown
        try:
            value = datetime.strptime(match.group(1).replace(",", ""), "%d %b %Y").date()
        except ValueError:
            return unknown
        return {
            **unknown,
            "published_date": value.isoformat(),
            "timezone_basis": f"source offset {match.group(2)}" if match.group(2) else "unknown",
            "publication_precision": "date",
        }
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            value = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return unknown
    if value.tzinfo is None or value.utcoffset() is None:
        return unknown
    return {
        **unknown,
        "published_at_utc": value.astimezone(timezone.utc).isoformat(),
        "timezone_basis": f"source offset {value.strftime('%z')}",
        "publication_precision": "second" if re.search(r"\d{1,2}:\d{2}:\d{2}", raw) else "minute",
    }


def parse_feed(provider: str, body: bytes, fetched_at: datetime) -> dict:
    """Parse RSS without inventing source dates, issuer mappings, or feed coverage."""
    if provider not in SOURCES:
        raise ValueError("Source is not enabled")
    if fetched_at.tzinfo is None or fetched_at.utcoffset() is None:
        raise ValueError("fetched_at must be timezone aware")
    if len(body) > MAX_BYTES or re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", body, re.I):
        return {"status": "malformed_feed", "items": [], "error": "unsafe or oversized XML"}
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        if re.search(rb"captcha|verify you are human|checking your browser", body, re.I):
            return {"status": "challenge", "items": [], "error": "challenge response"}
        if re.search(rb"<\s*(?:!doctype\s+html|html)\b", body, re.I):
            return {"status": "non_feed", "items": [], "error": "HTML response"}
        return {"status": "malformed_feed", "items": [], "error": str(exc)}
    if root.tag.lower() != "rss" or root.find("channel") is None:
        challenge = re.search(rb"captcha|verify you are human|checking your browser", body, re.I)
        return {
            "status": "challenge" if challenge else "non_feed",
            "items": [],
            "error": "expected RSS channel",
        }
    channel = root.find("channel")
    entries = channel.findall("item")
    output = []
    for entry in entries:
        title = (entry.findtext("title") or "").strip()
        url = (entry.findtext("link") or "").strip()
        guid = (entry.findtext("guid") or "").strip()
        if not (title and url):
            continue
        # Keep feed source IDs namespaced in storage, while retaining the original GUID.
        identity = guid or url
        output.append(
            {
                "provider": provider,
                "source_id": identity,
                "provider_entry_id": guid or None,
                "source_type": SOURCES[provider][1],
                "canonical_url": url,
                "title": title,
                "summary": None,
                **publication_date(entry.findtext("pubDate")),
                "event_at": None,
                "fetched_at_utc": fetched_at.astimezone(timezone.utc).isoformat(),
                "identity_basis": "unmapped",
                "issuer_identifiers": [],
                "content_hash": hashlib.sha256(ET.tostring(entry)).hexdigest(),
            }
        )
    status = (
        ("partial" if len(output) < len(entries) else "ok")
        if output
        else ("empty" if not entries else "malformed_feed")
    )
    return {
        "status": status,
        "items": output,
        "entries_seen": len(entries),
        "entries_skipped": len(entries) - len(output),
        "coverage": "current feed window only; pagination and historical completeness unknown",
    }


def _request(url: str, domains: list[str], headers: dict, deadline: float) -> tuple:
    # Same exact-host, HTTPS-only, globally-routable DNS pinning policy as browser.fetch_public.
    from research_room.browser import validate_url

    for _ in range(1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("source deadline exceeded")
        host, port = validate_url(url, domains)
        addresses = {x[4][0] for x in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses):
            raise ValueError("Non-public DNS destination refused")
        timeout = min(12, remaining)
        conn = http.client.HTTPSConnection(host, port, timeout=timeout)
        raw = socket.create_connection((sorted(addresses)[0], port), timeout=timeout)
        try:
            conn.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
            part = urlsplit(url)
            conn.request(
                "GET",
                (part.path or "/") + (("?" + part.query) if part.query else ""),
                headers=headers,
            )
            response = conn.getresponse()
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("source response exceeds 1 MB")
            return response.status, dict(response.getheaders()), body, url
        finally:
            conn.close()
            raw.close()
    raise ValueError("redirect limit exceeded")


def _fetch_feed_local(
    provider: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    deadline: float | None = None,
    cancelled=None,
) -> dict:
    if provider not in SOURCES:
        raise ValueError("Source is not enabled")
    url = SOURCES[provider][0]
    deadline = deadline if deadline is not None else time.monotonic() + 25
    headers = {
        "User-Agent": "KeplerResearch/1.0 (read-only)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    attempts = []
    for attempt in range(2):
        if cancelled is not None and cancelled.is_set():
            return {"status": "cancelled", "items": [], "http_requests": attempt}
        if time.monotonic() >= deadline:
            return {"status": "deadline", "items": [], "http_requests": attempt}
        try:
            status, response_headers, body, final_url = _request(
                url, [urlsplit(url).hostname], headers, deadline
            )
            attempts.append({"attempt": attempt + 1, "http_status": status})
            normalized = {k.lower(): v for k, v in response_headers.items()}
            details = {
                "http_status": status,
                "http_requests": len(attempts)
                if all("http_status" in a for a in attempts)
                else None,
                "request_bound": attempt + 1,
                "attempts": attempts,
                "etag": normalized.get("etag"),
                "last_modified": normalized.get("last-modified"),
                "final_url": final_url,
            }
            if status == 304:
                return {"status": "not_modified", "items": [], **details}
            if status == 200:
                return {**parse_feed(provider, body, datetime.now(timezone.utc)), **details}
            if status not in (429, 500, 502, 503, 504) or attempt:
                return {"status": "http_error", "items": [], **details}
        except (OSError, ValueError, TimeoutError) as exc:
            attempts.append({"attempt": attempt + 1, "error": type(exc).__name__})
            if attempt:
                return {
                    "status": "fetch_error",
                    "items": [],
                    "error": str(exc),
                    "http_requests": None,
                    "request_bound": attempt + 1,
                    "attempts": attempts,
                }
        delay = min(1.0, max(0, deadline - time.monotonic()))
        if cancelled is not None and cancelled.wait(delay):
            return {"status": "cancelled", "items": [], "http_requests": attempt + 1}
        if cancelled is None:
            time.sleep(delay)
    raise AssertionError("unreachable")


def _feed_child(pipe, provider, etag, last_modified, deadline):
    try:
        pipe.send(
            _fetch_feed_local(provider, etag=etag, last_modified=last_modified, deadline=deadline)
        )
    except Exception as exc:
        pipe.send({"status": "fetch_error", "items": [], "error": str(exc), "http_requests": None})
    finally:
        pipe.close()


def fetch_feed(
    provider: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    deadline: float | None = None,
    cancelled=None,
) -> dict:
    """Supervise DNS and reads against a hard monotonic deadline; no hidden redirects."""
    if provider not in SOURCES:
        raise ValueError("Source is not enabled")
    deadline = deadline if deadline is not None else time.monotonic() + 25
    with _RATE_LOCK:
        now = time.monotonic()
        if now - _LAST_REQUEST.get(provider, float("-inf")) < MIN_REFRESH_SECONDS:
            return {"status": "rate_limited", "items": [], "http_requests": 0}
        if cancelled is not None and cancelled.is_set():
            return {"status": "cancelled", "items": [], "http_requests": 0}
        if now >= deadline:
            return {"status": "deadline", "items": [], "http_requests": 0}
        _LAST_REQUEST[provider] = now
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(
        target=_feed_child, args=(send, provider, etag, last_modified, deadline)
    )
    process.start()
    send.close()
    try:
        while True:
            if cancelled is not None and cancelled.is_set():
                return {
                    "status": "cancelled",
                    "items": [],
                    "http_requests": None,
                    "request_bound": 2,
                }
            left = deadline - time.monotonic()
            if left <= 0:
                return {
                    "status": "deadline",
                    "items": [],
                    "http_requests": None,
                    "request_bound": 2,
                }
            if receive.poll(min(0.1, left)):
                return receive.recv()
            if not process.is_alive():
                return {
                    "status": "fetch_error",
                    "items": [],
                    "http_requests": None,
                    "request_bound": 2,
                    "error": "fetch worker exited",
                }
    finally:
        receive.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join()
