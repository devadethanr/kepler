from __future__ import annotations

from swingtradev3.auth.kite.client import extract_request_token


def test_extract_request_token_from_full_url() -> None:
    token = extract_request_token(
        "http://localhost:8080/?status=success&request_token=abc123&action=login&type=login"
    )
    assert token == "abc123"


def test_extract_request_token_from_raw_token() -> None:
    assert extract_request_token("raw-token-123") == "raw-token-123"
