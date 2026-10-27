"""
Pytest configuration — patch Google discovery/JWKS fetches so tests run offline.
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def mock_google_oidc():
    """Prevent real network calls to Google during tests."""
    fake_discovery = {
        "issuer": "https://accounts.google.com",
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
    }
    fake_jwks = {"keys": []}

    with (
        patch(
            "app.services.google_auth._get_discovery",
            new=AsyncMock(return_value=fake_discovery),
        ),
        patch(
            "app.services.google_auth.get_jwks",
            new=AsyncMock(return_value=fake_jwks),
        ),
    ):
        yield
