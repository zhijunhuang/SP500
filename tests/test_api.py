"""
Acceptance tests for API endpoints.

Tests:
- /api/sp500/{date} - requires valid token + active subscription
- /api/meta - no auth required
- Various auth error cases
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, APIToken, SP500Constituent


class TestSP500Endpoint:
    """Tests for /api/sp500/{target_date} endpoint."""

    def test_no_authorization_header(self, client: TestClient, test_db: Session):
        """Request without Authorization header should return 401."""
        response = client.get("/api/sp500/2024-01-01")
        assert response.status_code == 401
        assert "未提供认证令牌" in response.json()["detail"]

    def test_invalid_bearer_token(self, client: TestClient, test_db: Session):
        """Invalid token should return 401."""
        response = client.get(
            "/api/sp500/2024-01-01",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401
        assert "无效的API令牌" in response.json()["detail"]

    def test_expired_subscription(self, client: TestClient, sample_expired_user: User, test_db: Session):
        """Expired subscription should return 403."""
        # Create token for expired user
        import hashlib, secrets
        plain_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()

        api_token = APIToken(
            user_id=sample_expired_user.id,
            name="Expired User Token",
            token_hash=token_hash,
            revoked=False
        )
        test_db.add(api_token)
        test_db.commit()

        response = client.get(
            "/api/sp500/2024-01-01",
            headers={"Authorization": f"Bearer {plain_token}"}
        )
        assert response.status_code == 403
        assert "订阅已过期" in response.json()["detail"]

    def test_valid_request_returns_constituents(
        self,
        client: TestClient,
        sample_api_token: tuple[str, APIToken],
        sample_constituents: list[SP500Constituent],
        sample_meta
    ):
        """Valid request should return constituents list."""
        plain_token, _ = sample_api_token

        response = client.get(
            "/api/sp500/2024-01-01",
            headers={"Authorization": f"Bearer {plain_token}"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["date"] == "2024-01-01"
        assert "constituents" in data
        assert "meta" in data

        # Should include AAPL, MSFT, GOOGL, IBM, TSLA (all added before Jan 2024)
        codes = [c["code"] for c in data["constituents"]]
        assert "AAPL" in codes
        assert "MSFT" in codes
        assert "GOOGL" in codes
        assert "IBM" in codes
        assert "TSLA" in codes  # Added Dec 2020, so Jan 2024 is within range

    def test_date_filter_removed_constituent(
        self,
        client: TestClient,
        sample_api_token: tuple[str, APIToken],
        sample_constituents: list[SP500Constituent],
        sample_meta
    ):
        """IBM should not appear for dates after its removal (2024-06-01)."""
        plain_token, _ = sample_api_token

        # Query after IBM removal date
        response = client.get(
            "/api/sp500/2024-06-15",
            headers={"Authorization": f"Bearer {plain_token}"}
        )
        assert response.status_code == 200

        codes = [c["code"] for c in response.json()["constituents"]]
        assert "IBM" not in codes  # IBM effective_to is 2024-06-01

    def test_revoked_token_rejected(
        self,
        client: TestClient,
        sample_user: User,
        test_db: Session
    ):
        """Revoked token should be rejected."""
        import hashlib, secrets
        plain_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()

        api_token = APIToken(
            user_id=sample_user.id,
            name="Revoked Token",
            token_hash=token_hash,
            revoked=True  # Revoked!
        )
        test_db.add(api_token)
        test_db.commit()

        response = client.get(
            "/api/sp500/2024-01-01",
            headers={"Authorization": f"Bearer {plain_token}"}
        )
        assert response.status_code == 401
        assert "无效的API令牌" in response.json()["detail"]


class TestMetaEndpoint:
    """Tests for /api/meta endpoint (no auth required)."""

    def test_meta_no_auth_required(self, client: TestClient, sample_meta):
        """Meta endpoint should work without authentication."""
        response = client.get("/api/meta")
        assert response.status_code == 200

        data = response.json()
        assert "data_source" in data
        assert data["data_source"] == "Wikipedia - List of S&P 500 companies"

    def test_meta_empty_when_no_data(self, client: TestClient, test_db: Session):
        """Meta endpoint should return empty dict when no meta exists."""
        response = client.get("/api/meta")
        assert response.status_code == 200
        assert response.json() == {}
