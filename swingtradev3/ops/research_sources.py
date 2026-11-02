"""Controlled source refresh using the installed host database configuration.

No schema upgrade, broker control, model request, or automatic provider fallback.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def main():
    if not os.environ.get("DATABASE_URL"):
        filename = Path.home() / ".local/state/kepler-rooms/worker.env"
        if not filename.is_file():
            raise RuntimeError("Configure DATABASE_URL or run the existing research-start setup first")
        values = dict(line.split("=", 1) for line in filename.read_text().splitlines() if line)
        os.environ["DATABASE_URL"] = json.loads(values["DATABASE_URL"])
    from data.news.ingest_sources import main as refresh

    refresh()


if __name__ == "__main__":
    main()
