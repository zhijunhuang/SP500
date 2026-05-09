"""
Acceptance tests for tokens router.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import APIToken


class TestTokensPage:
    """Tests for /tokens page."""

    def test_tokens_page_requires_login(self, client: TestClient):
        """Tokens page should require authentication."""
        response = client.get("/tokens")
        assert response.status_code == 401

    def test_tokens_page_loads_with_session(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user
    ):
        """Tokens page should load for authenticated user."""
        response = client.get(
            "/tokens",
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestCreateToken:
    """Tests for /tokens/create endpoint."""

    def test_create_token_requires_login(self, client: TestClient):
        """Create token should require authentication."""
        response = client.post("/tokens/create", data={"name": "Test Token"})
        assert response.status_code == 401

    def test_create_token_success(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user,
        test_db: Session
    ):
        """Create token should return the plain token."""
        response = client.post(
            "/tokens/create",
            data={"name": "My Test Token"},
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["name"] == "My Test Token"
        # Token should be a non-empty string
        assert len(data["token"]) > 20

    def test_create_token_stores_hash(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user,
        test_db: Session
    ):
        """Create token should store hash, not plain token."""
        response = client.post(
            "/tokens/create",
            data={"name": "Hash Test Token"},
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 200
        plain_token = response.json()["token"]

        # Verify hash is stored (not plain token)
        import hashlib
        expected_hash = hashlib.sha256(plain_token.encode()).hexdigest()

        stored_token = test_db.query(APIToken).filter(
            APIToken.token_hash == expected_hash
        ).first()
        assert stored_token is not None
        assert stored_token.name == "Hash Test Token"


class TestDeleteToken:
    """Tests for /tokens/delete endpoint."""

    def test_delete_token_requires_login(self, client: TestClient):
        """Delete token should require authentication."""
        response = client.post("/tokens/delete", data={"token_id": 1})
        assert response.status_code == 401

    def test_delete_token_success(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_api_token,
        test_db: Session
    ):
        """Delete token should mark it as revoked."""
        plain_token, api_token = sample_api_token

        response = client.post(
            "/tokens/delete",
            data={"token_id": api_token.id},
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "令牌已删除"

        # Verify token is revoked
        test_db.refresh(api_token)
        assert api_token.revoked is True

    def test_delete_nonexistent_token(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user
    ):
        """Delete nonexistent token should return 404."""
        response = client.post(
            "/tokens/delete",
            data={"token_id": 99999},
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 404
        assert "令牌不存在" in response.json()["detail"]


class TestCopyToken:
    """Tests for /tokens/copy endpoint."""

    def test_copy_token_requires_login(self, client: TestClient):
        """Copy token should require authentication."""
        response = client.post("/tokens/copy", data={"token_id": 1, "new_name": "Copy"})
        assert response.status_code == 401

    def test_copy_token_success(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_api_token,
        test_db: Session
    ):
        """Copy token should create new token with same hash."""
        plain_token, original = sample_api_token

        response = client.post(
            "/tokens/copy",
            data={"token_id": original.id, "new_name": "Copied Token"},
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["name"] == "Copied Token"

    def test_copy_nonexistent_token(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user
    ):
        """Copy nonexistent token should return 404."""
        response = client.post(
            "/tokens/copy",
            data={"token_id": 99999, "new_name": "Copy"},
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 404
        assert "令牌不存在" in response.json()["detail"]
