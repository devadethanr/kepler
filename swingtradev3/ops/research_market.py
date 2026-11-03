"""Save read-only market availability using the installed private DB configuration."""

import json
import os
from pathlib import Path


def main():
    if not os.environ.get("DATABASE_URL"):
        filename = Path.home() / ".local/state/kepler-rooms/worker.env"
        values = dict(line.split("=", 1) for line in filename.read_text().splitlines() if line)
        os.environ["DATABASE_URL"] = json.loads(values["DATABASE_URL"])
    from data.market_context.refresh import refresh

    print(json.dumps(refresh(), indent=2))


if __name__ == "__main__":
    main()
