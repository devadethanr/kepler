"""One bounded PIB HTML extraction, with no crawler or browser profile."""

from __future__ import annotations

import hashlib
import re
import time
from urllib.parse import parse_qs, urlsplit

from research_room.browser import _supervised_fetch

# PIB permits accurate reproduction with acknowledgment, excluding third-party material:
# https://www.pib.gov.in/content/102_2_Copyright-Policy.aspx?lang=1&reg=30
# The caller must check whether a selected release contains excluded third-party material.
PIB_HOSTS = ["www.pib.gov.in", "pib.gov.in"]
PIB_PATHS = {"/PressReleasePage.aspx", "/PressReleaseIframePage.aspx"}


def parse_pib_release(body: bytes, source_url: str) -> dict:
    """Extract a bounded, attributed text excerpt from the reviewed PIB release."""
    parsed = urlsplit(source_url)
    query = parse_qs(parsed.query)
    release_ids = query.get("PRID", [])
    if (
        parsed.scheme != "https"
        or parsed.netloc not in PIB_HOSTS
        or parsed.path not in PIB_PATHS
        or len(release_ids) != 1
        or not re.fullmatch(r"[0-9]{1,12}", release_ids[0])
        or parsed.fragment
    ):
        raise ValueError("PIB release is outside the reviewed scope")
    if len(body) > 1_000_000:
        raise ValueError("HTML exceeds 1 MB")
    from scrapling.parser import Selector

    document = Selector(body)
    title = document.css("#Titleh2")
    release_id = document.css("#ReleaseId")
    paragraphs = document.css("#pibReleaseBody p")
    posted = document.css("#PrDateTime")
    published_raw = re.sub(r"\s+", " ", posted[0].get_all_text()).strip() if posted else None
    precision = "unknown"
    if published_raw:
        match = re.search(
            r"\b(\d{1,2} [A-Za-z]{3} \d{4} \d{1,2}:\d{2}\s*[AP]M)\b", published_raw, re.I
        )
        if match:
            from datetime import datetime

            try:
                datetime.strptime(re.sub(r"\s+", " ", match.group(1)).upper(), "%d %b %Y %I:%M%p")
            except ValueError:
                pass
            else:
                precision = "minute"
    if (
        not title
        or not release_id
        or not re.search(r"\b" + re.escape(release_ids[0]) + r"\b", release_id[0].get_all_text())
        or not paragraphs
    ):
        return {"status": "unavailable", "reason": "expected release selectors absent"}
    # Only paragraphs without external media/links are selected; do not infer image text.
    parts = [
        re.sub(r"\s+", " ", p.get_all_text()).strip()
        for p in paragraphs
        if not p.css("img, a, video, iframe")
    ]
    parts = [part for part in parts if part]
    text = "\n\n".join(parts)
    excerpt = text[:1200]
    return {
        "status": "ok" if excerpt else "unavailable",
        "source_url": source_url,
        "source_owner": "Press Information Bureau, Government of India",
        "provider_entry_id": release_ids[0],
        "published_raw": published_raw,
        "published_at_utc": None,
        "published_date": None,
        "publication_precision": precision,
        "timezone_basis": "unknown",
        "event_at": None,
        "period": None,
        "units": None,
        "currency": None,
        "title": re.sub(r"\s+", " ", title[0].get_all_text()).strip(),
        "excerpt": excerpt,
        "offset": 0,
        "end_offset": len(excerpt),
        "offset_basis": "normalized selected PIB text characters",
        "truncated": len(text) > len(excerpt),
        "completeness": "partial: text paragraphs only; images and attachments excluded",
        "source_hash": hashlib.sha256(body).hexdigest(),
        "terms": "PIB reproduction with attribution; third-party permission must be verified",
    }


def fetch_pib_release(url: str, *, deadline: float | None = None, cancelled=None) -> dict:
    """Fetch one PIB release under the existing supervised public fetch policy."""
    deadline = deadline if deadline is not None else time.monotonic() + 25
    if deadline <= time.monotonic() or (cancelled is not None and cancelled.is_set()):
        return {"status": "unavailable", "reason": "deadline or cancellation"}
    try:
        parsed = urlsplit(url)
        query = parse_qs(parsed.query)
        ids = query.get("PRID", [])
        if (
            parsed.scheme != "https"
            or parsed.netloc not in PIB_HOSTS
            or parsed.path not in PIB_PATHS
            or len(ids) != 1
            or not re.fullmatch(r"[0-9]{1,12}", ids[0])
            or parsed.fragment
        ):
            raise ValueError("PIB release is outside the permitted scope")
        body, url = _supervised_fetch(url, PIB_HOSTS, deadline, cancelled)
        return parse_pib_release(body, url)
    except (ValueError, OSError, RuntimeError, TimeoutError) as exc:
        return {"status": "unavailable", "reason": str(exc)}
