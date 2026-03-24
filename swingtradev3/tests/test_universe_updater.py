from __future__ import annotations

from pathlib import Path

from swingtradev3.data.nifty50_loader import Nifty50Loader
from swingtradev3.data.nifty200_loader import Nifty200Loader
from swingtradev3.data.universe_updater import UniverseUpdater


def test_extract_constituent_url() -> None:
    html = """
    <html>
      <body>
        <a href="/content/indices/ind_nifty50list.csv">Index Constituent</a>
      </body>
    </html>
    """

    url = UniverseUpdater._extract_constituent_url(
        html,
        "https://www.niftyindices.com/indices/equity/broad-based-indices/nifty--50",
    )

    assert url == "https://www.niftyindices.com/content/indices/ind_nifty50list.csv"


def test_parse_constituent_csv() -> None:
    payload = "Company Name,Symbol\nInfosys Ltd,INFY\nState Bank of India,SBIN\n"

    entries = UniverseUpdater._parse_constituent_csv(payload)

    assert entries == [
        {"ticker": "INFY", "name": "Infosys Ltd"},
        {"ticker": "SBIN", "name": "State Bank of India"},
    ]


def test_refresh_all_writes_loader_outputs(tmp_path: Path) -> None:
    class StubUpdater(UniverseUpdater):
        def _fetch_constituents(self, index_key: str) -> list[dict[str, str]]:
            if index_key == "nifty50":
                return [{"ticker": "INFY", "name": "Infosys Ltd"}]
            if index_key == "nifty200":
                return [{"ticker": "SBIN", "name": "State Bank of India"}]
            raise AssertionError(index_key)

    updater = StubUpdater(
        nifty50_loader=Nifty50Loader(cache_path=tmp_path / "nifty50.json"),
        nifty200_loader=Nifty200Loader(cache_path=tmp_path / "nifty200.json"),
    )

    counts = updater.refresh_all()

    assert counts == {"nifty50": 1, "nifty200": 1}
    assert updater.nifty50_loader.load_entries() == [{"ticker": "INFY", "name": "Infosys Ltd"}]
    assert updater.nifty200_loader.load_entries() == [{"ticker": "SBIN", "name": "State Bank of India"}]
