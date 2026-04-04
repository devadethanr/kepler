from __future__ import annotations

import argparse
import asyncio
import json

from auth.kite.client import build_kite_client, exchange_request_token, extract_request_token
from logging_config import setup_logging
from paths import ensure_runtime_dirs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange a Zerodha request_token for a Kite session")
    parser.add_argument("--request-token", help="Optional raw request_token or full redirected URL")
    return parser


async def _run(request_token_arg: str | None) -> int:
    client = build_kite_client()
    print("Open this URL in your browser and complete the Kite authorization flow:")
    print(client.login_url())
    print("")
    print("After login, copy the full redirected URL from the browser address bar and paste it here.")
    print("You can also paste only the request_token.")

    supplied = request_token_arg or await asyncio.to_thread(input, "Redirected URL or request_token: ")

    try:
        request_token = extract_request_token(supplied)
        session = exchange_request_token(request_token)
    except Exception as exc:
        print("")
        print(f"Kite session exchange failed: {exc}")
        return 1

    print("")
    print("Authenticated Kite session:")
    print(
        json.dumps(
            {
                "user_id": session.user_id,
                "user_name": session.user_name,
                "user_shortname": session.user_shortname,
                "email": session.email,
                "broker": session.broker,
                "user_type": session.user_type,
                "login_time": session.login_time,
            },
            indent=2,
        )
    )
    print("")
    print("Session saved to swingtradev3/context/auth/kite_session.json")
    return 0


def main() -> None:
    ensure_runtime_dirs()
    setup_logging()
    args = _build_parser().parse_args()
    raise SystemExit(asyncio.run(_run(args.request_token)))


if __name__ == "__main__":
    main()
