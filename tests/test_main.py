"""
Acceptance tests for main app pages (index, dashboard).
"""
import pytest
from fastapi.testclient import TestClient


class TestIndexPage:
    """Tests for the index page (/)."""

    def test_index_page_returns_html(self, client: TestClient):
        """Index page should return HTML without authentication."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestDashboardPage:
    """Tests for the dashboard page (/dashboard)."""

    def test_dashboard_redirects_unauthenticated(self, client: TestClient):
        """Dashboard should redirect to login if not authenticated."""
        # Don't follow redirects - check the initial 302 response
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

    def test_dashboard_loads_for_authenticated_user(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user
    ):
        """Dashboard should load for authenticated user."""
        response = client.get(
            "/dashboard",
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
