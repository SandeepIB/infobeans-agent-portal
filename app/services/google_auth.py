from __future__ import annotations
import logging
import time
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
_discovery_cache: dict[str, Any] | None = None


async def _get_discovery() -> dict[str, Any]:
    global _discovery_cache
    if _discovery_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(GOOGLE_DISCOVERY_URL, timeout=10)
            resp.raise_for_status()
            _discovery_cache = resp.json()
    return _discovery_cache


async def get_jwks() -> dict[str, Any]:
    discovery = await _get_discovery()
    async with httpx.AsyncClient() as client:
        resp = await client.get(discovery["jwks_uri"], timeout=10)
        resp.raise_for_status()
        return resp.json()


async def get_authorization_url(state: str) -> str:
    discovery = await _get_discovery()
    import urllib.parse
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    }
    if settings.google_allowed_domain:
        # Restricts the Google account chooser to the workspace domain (UX only).
        # The hard enforcement happens in extract_verified_email() after token verification.
        params["hd"] = settings.google_allowed_domain
    return discovery["authorization_endpoint"] + "?" + urllib.parse.urlencode(params)


async def exchange_code(code: str) -> dict[str, Any]:
    discovery = await _get_discovery()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            discovery["token_endpoint"],
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


def verify_id_token(id_token_str: str, jwks_data: dict[str, Any]) -> dict[str, Any]:
    from joserfc import jwt
    from joserfc.jwk import KeySet

    keyset = KeySet.import_key_set(jwks_data)
    token = jwt.decode(id_token_str, keyset)

    claims = token.claims
    now = int(time.time())

    iss = claims.get("iss", "")
    if iss not in ("https://accounts.google.com", "accounts.google.com"):
        raise ValueError(f"Invalid issuer: {iss!r}")

    aud = claims.get("aud")
    if isinstance(aud, str):
        aud = [aud]
    if settings.google_client_id not in aud:
        raise ValueError("Token audience does not match client_id")

    exp = claims.get("exp", 0)
    if exp < now:
        raise ValueError("Token has expired")

    return claims


def extract_verified_email(claims: dict[str, Any]) -> str:
    if not claims.get("email_verified"):
        raise ValueError("Google has not verified this email address")
    email: str = claims.get("email", "")
    if not email:
        raise ValueError("No email in Google token claims")
    if settings.google_allowed_domain:
        allowed = settings.google_allowed_domain.lower()
        domain = email.split("@", 1)[-1].lower()
        if domain != allowed:
            raise ValueError(f"Email domain @{domain} is not allowed; must be @{allowed}")
        # Google Workspace ID tokens include the `hd` claim — verify it too.
        hd = claims.get("hd", "").lower()
        if hd and hd != allowed:
            raise ValueError(f"Token hd claim {hd!r} does not match allowed domain {allowed!r}")
    return email.strip().lower()
