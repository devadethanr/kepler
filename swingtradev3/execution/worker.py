from __future__ import annotations

import asyncio

from .bootstrap import WorkerLockUnavailable, WorkerRuntime


async def _run() -> int:
    runtime = WorkerRuntime()
    try:
        await runtime.run_forever()
    except WorkerLockUnavailable as exc:
        print(f"worker did not start: {exc}")
        return 0
    finally:
        if runtime._started:
            await runtime.stop()
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
