"""
Kite Login Helper
==================
Manual browser login → request_token → access_token exchange → session save.

Usage:
    docker compose -f docker-compose.dev.yml exec -it app python auth/kite/login.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from kiteconnect import KiteConnect

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONTEXT_AUTH = PROJECT_ROOT / "context" / "auth"
ENV_FILE = PROJECT_ROOT / ".env"


def load_env():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and value and key not in os.environ:
            os.environ[key] = value


def get_kite_api_key():
    return os.environ.get("KITE_API_KEY", "")


def get_kite_api_secret():
    return os.environ.get("KITE_API_SECRET", "")


def extract_request_token(url_or_token: str) -> str:
    if url_or_token.startswith("http"):
        parsed = urlparse(url_or_token)
        params = parse_qs(parsed.query)
        if "request_token" in params:
            return params["request_token"][0]
    return url_or_token.strip()


def exchange_request_token(request_token: str) -> dict:
    api_key = get_kite_api_key()
    api_secret = get_kite_api_secret()
    if not api_key or not api_secret:
        raise ValueError("KITE_API_KEY and KITE_API_SECRET must be set in .env")
    kite = KiteConnect(api_key=api_key)
    return kite.generate_session(request_token, api_secret=api_secret)


def save_session(session: dict) -> Path:
    CONTEXT_AUTH.mkdir(parents=True, exist_ok=True)
    session_file = CONTEXT_AUTH / "kite_session.json"

    def default_serializer(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    session_file.write_text(json.dumps(session, indent=2, default=default_serializer))
    return session_file


def verify_session(access_token: str) -> dict:
    api_key = get_kite_api_key()
    kite = KiteConnect(api_key=api_key, access_token=access_token)
    return kite.profile()


def main():
    parser = argparse.ArgumentParser(description="Exchange a Zerodha request_token for a Kite session")
    parser.add_argument("--request-token", help="Optional raw request_token or full redirected URL")
    args = parser.parse_args()

    load_env()
    api_key = get_kite_api_key()

    if not api_key:
        print("ERROR: KITE_API_KEY not set in .env")
        sys.exit(1)

    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()

    print("=" * 60)
    print("KITE LOGIN HELPER")
    print("=" * 60)
    print()
    print("Step 1: Open this URL in your browser:")
    print(f"  {login_url}")
    print()
    print("Step 2: Complete login and authorization in the browser.")
    print()
    print("Step 3: Copy the full redirected URL from the browser address bar")
    print("        and paste it below.")
    print("        (You can also paste just the request_token)")
    print()

    supplied = args.request_token or input("Redirected URL or request_token: ").strip()
    if not supplied:
        print("ERROR: No input provided")
        sys.exit(1)

    try:
        request_token = extract_request_token(supplied)
        print(f"\nExchanged request_token: {request_token[:20]}...")

        session = exchange_request_token(request_token)
        access_token = session.get("access_token", "")

        print("\nVerifying session...")
        profile = verify_session(access_token)

        print("\n" + "=" * 60)
        print("AUTHENTICATED KITE SESSION")
        print("=" * 60)
        print(f"  User ID:     {profile.get('user_id', 'N/A')}")
        print(f"  User Name:   {profile.get('user_name', 'N/A')}")
        print(f"  Email:       {profile.get('email', 'N/A')}")
        print(f"  Broker:      {profile.get('broker', 'N/A')}")
        print(f"  User Type:   {profile.get('user_type', 'N/A')}")
        print(f"  Login Time:  {profile.get('login_time', 'N/A')}")
        print(f"  Access Token: {access_token[:20]}...")

        session_path = save_session(session)
        print(f"\nSession saved to: {session_path}")
        print("=" * 60)

    except Exception as exc:
        print(f"\nERROR: Kite session exchange failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
