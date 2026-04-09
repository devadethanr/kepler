from __future__ import annotations


def generate_totp(secret: str) -> str:
    import pyotp

    return pyotp.TOTP(secret).now()
