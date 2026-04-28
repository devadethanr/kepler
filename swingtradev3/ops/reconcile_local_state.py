from __future__ import annotations

import sys

from ops.phase0_check import format_reconcile_report, reconcile_local_state


def main() -> None:
    result = reconcile_local_state()
    print(format_reconcile_report(result))
    if result.missing_local:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
