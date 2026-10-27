"""
Route-level smoke tests using HTTPX TestClient (no real Google OAuth required).
These tests verify HTTP status codes and security behaviour without touching
external services or requiring real credentials.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


class TestPublicRoutes:
    def test_home_returns_200(self):
        r = client.get("/")
        assert r.status_code == 200

    def test_home_contains_login_link(self):
        r = client.get("/")
        assert "/auth/google/login" in r.text

    def test_static_css_served(self):
        r = client.get("/static/portal.css")
        assert r.status_code == 200
        assert "text/css" in r.headers.get("content-type", "")

    def test_login_redirects_to_google(self):
        r = client.get("/auth/google/login", follow_redirects=False)
        assert r.status_code == 302
        location = r.headers["location"]
        assert "accounts.google.com" in location or "google" in location.lower()

    def test_login_redirect_contains_state(self):
        r = client.get("/auth/google/login", follow_redirects=False)
        assert "state=" in r.headers["location"]

    def test_logout_get_redirects(self):
        r = client.get("/logout", follow_redirects=False)
        assert r.status_code in (302, 303)

    def test_logout_post_redirects(self):
        r = client.post("/logout", follow_redirects=False)
        assert r.status_code in (302, 303)


class TestProtectedApiRoutes:
    def test_api_me_requires_auth(self):
        r = client.get("/api/me")
        assert r.status_code == 401

    def test_api_apps_requires_auth(self):
        r = client.get("/api/apps")
        assert r.status_code == 401

    def test_admin_dashboard_requires_auth(self):
        r = client.get("/admin", follow_redirects=False)
        assert r.status_code == 401

    def test_admin_users_requires_auth(self):
        r = client.get("/admin/users", follow_redirects=False)
        assert r.status_code == 401

    def test_admin_apps_requires_auth(self):
        r = client.get("/admin/apps", follow_redirects=False)
        assert r.status_code == 401

    def test_admin_permissions_requires_auth(self):
        r = client.get("/admin/permissions", follow_redirects=False)
        assert r.status_code == 401

    def test_admin_api_users_requires_auth(self):
        r = client.get("/admin/api/users")
        assert r.status_code == 401

    def test_admin_api_apps_requires_auth(self):
        r = client.get("/admin/api/apps")
        assert r.status_code == 401


class TestSecurityHeaders:
    def test_home_has_x_frame_options(self):
        r = client.get("/")
        assert "x-frame-options" in r.headers

    def test_home_has_x_content_type_options(self):
        r = client.get("/")
        assert r.headers.get("x-content-type-options") == "nosniff"

    def test_home_has_csp(self):
        r = client.get("/")
        assert "content-security-policy" in r.headers


class TestOAuthCallbackCSRF:
    def test_callback_without_state_returns_error(self):
        r = client.get("/auth/google/callback?code=abc")
        # Should not succeed — state mismatch; hub shows the login page with an error banner
        assert r.status_code in (400, 422, 200)
        body = r.text.lower()
        assert any(word in body for word in ("security check", "failed", "error", "invalid"))

    def test_callback_with_wrong_state_returns_error(self):
        r = client.get("/auth/google/callback?code=abc&state=wrong_state")
        assert r.status_code in (400, 200)
        body = r.text.lower()
        assert any(word in body for word in ("security check", "failed", "error", "invalid"))
