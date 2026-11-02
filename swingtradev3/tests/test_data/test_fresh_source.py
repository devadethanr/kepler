from datetime import datetime, timezone

from data.news.fresh_source import parse_feed, publication_date

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)


def test_date_only_offset_is_not_invented_timestamp():
    result = publication_date("30 Oct, 2026 +0530")
    assert result["published_date"] == "2026-10-30"
    assert result["published_at_utc"] is None
    assert result["timezone_basis"] == "source offset +0530"
    assert result["publication_precision"] == "date"


def test_timestamp_requires_explicit_zone_and_retains_offset():
    assert (
        publication_date("Fri, 30 Oct 2026 17:30:00 +0530")["published_at_utc"]
        == "2026-10-30T12:00:00+00:00"
    )
    assert publication_date("2026-10-30T17:30:00")["publication_precision"] == "unknown"
    assert publication_date("not a date")["publication_precision"] == "unknown"


def test_feed_metadata_and_empty_or_bad_feed():
    xml = b"""<rss><channel><item><title>Notice</title><link>https://www.sebi.gov.in/a</link><pubDate>30 Oct, 2026 +0530</pubDate><description>Do not retain</description></item></channel></rss>"""
    parsed = parse_feed("sebi_rss", xml, NOW)
    assert parsed["status"] == "ok"
    assert parsed["items"][0]["summary"] is None
    assert parsed["items"][0]["identity_basis"] == "unmapped"
    assert parse_feed("sebi_rss", b"<rss><channel/></rss>", NOW)["status"] == "empty"
    assert parse_feed("sebi_rss", b"<html></html>", NOW)["status"] == "non_feed"
    assert parse_feed("sebi_rss", b"<!DOCTYPE rss><rss/>", NOW)["status"] == "malformed_feed"


def test_partial_feed_is_not_complete():
    xml = b"<rss><channel><item><title>Notice</title><link>https://example.org/1</link></item><item><title>Missing link</title></item></channel></rss>"
    result = parse_feed("sebi_rss", xml, NOW)
    assert result["status"] == "partial"
    assert result["entries_seen"] == 2
    assert result["entries_skipped"] == 1


def test_news_package_import_stays_narrow():
    import subprocess
    import sys

    code = (
        "import sys; import data.news as n; "
        "assert callable(n.clean_text); "
        "assert 'data.news.aggregator' not in sys.modules; "
        "from data.news.fresh_source import publication_date; "
        "assert publication_date('30 Oct, 2026 +0530')['published_date'] == '2026-10-30'"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_scrapling_pib_excerpt_is_bounded_and_rejects_other_pages():
    import pytest

    pytest.importorskip("scrapling.parser")
    from data.news.fresh_source_html import parse_pib_release

    html = b'<h1 id="Titleh2">Notice</h1><span id="ReleaseId">(Release ID: 2317034)</span><div id="PrDateTime">Posted On: 30 SEP 2026 4:41PM by PIB Delhi</div><div id="pibReleaseBody"><p>Example text.</p><p><img src="x">Excluded media</p></div>'
    result = parse_pib_release(html, "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2317034")
    assert result["excerpt"] == "Example text."
    assert result["published_raw"] == "Posted On: 30 SEP 2026 4:41PM by PIB Delhi"
    assert result["publication_precision"] == "minute"
    assert result["timezone_basis"] == "unknown"
    assert result["published_at_utc"] is None
    assert result["end_offset"] == len(result["excerpt"])
    assert (
        parse_pib_release(html, "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1")["status"]
        == "unavailable"
    )
    with pytest.raises(ValueError):
        parse_pib_release(html, "https://example.com/PressReleasePage.aspx?PRID=1")
