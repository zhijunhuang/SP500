"""
Acceptance tests for authentication flow.

Tests:
- send-code rate limiting (1 minute)
- verify-code with correct/incorrect codes
- verify-code 5 failed attempts triggers lockout
- logout clears session
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, EmailLoginCode


class TestSendCode:
    """Tests for /auth/send-code endpoint."""

    def test_send_code_success(self, client: TestClient, test_db: Session):
        """First code request should succeed."""
        response = client.post(
            "/auth/send-code",
            data={"email": "newuser@example.com"}
        )
        assert response.status_code == 200
        assert "验证码已发送" in response.json()["message"]

    def test_send_code_rate_limited(self, client: TestClient, test_db: Session):
        """Second request within 1 minute should be rate limited."""
        email = "ratelimit@example.com"

        # First request
        response1 = client.post("/auth/send-code", data={"email": email})
        assert response1.status_code == 200

        # Second request within 1 minute should fail
        response2 = client.post("/auth/send-code", data={"email": email})
        assert response2.status_code == 200
        assert "1分钟内只能发送一次验证码" in response2.json()["message"]


class TestVerifyCode:
    """Tests for /auth/verify-code endpoint."""

    def test_verify_code_success(self, client: TestClient, test_db: Session):
        """Correct code should redirect to dashboard and create session."""
        email = "verify@example.com"

        # Send code first
        client.post("/auth/send-code", data={"email": email})

        # Get the code from database
        login_code = test_db.query(EmailLoginCode).filter(
            EmailLoginCode.email == email,
            EmailLoginCode.used == False
        ).first()
        assert login_code is not None

        # Verify with correct code - don't follow redirect to capture the cookie
        response = client.post(
            "/auth/verify-code",
            data={"email": email, "code": login_code.code},
            follow_redirects=False
        )
        # Should get 302 redirect to dashboard with session cookie
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"
        assert "session" in response.cookies

    def test_verify_code_wrong_code(self, client: TestClient, test_db: Session):
        """Wrong code should return 400 error."""
        email = "wrong@example.com"

        # Send code first
        client.post("/auth/send-code", data={"email": email})

        # Try wrong code
        response = client.post(
            "/auth/verify-code",
            data={"email": email, "code": "000000"}
        )
        assert response.status_code == 400
        assert "验证码无效或已过期" in response.json()["detail"]

    def test_verify_code_expired(self, client: TestClient, test_db: Session):
        """Expired code should return 400 error."""
        email = "expired@example.com"

        # Create an old used code
        from datetime import datetime, timedelta
        old_code = EmailLoginCode(
            email=email,
            code="123456",
            created_at=datetime.utcnow() - timedelta(minutes=10),
            used=False
        )
        test_db.add(old_code)
        test_db.commit()

        # Try to verify expired code
        response = client.post(
            "/auth/verify-code",
            data={"email": email, "code": "123456"}
        )
        assert response.status_code == 400
        assert "验证码无效或已过期" in response.json()["detail"]

    def test_verify_code_5_failed_attempts_lockout(self, client: TestClient, test_db: Session):
        """5 failed attempts should trigger lockout (429)."""
        email = "lockout@example.com"

        # Send a valid code first
        client.post("/auth/send-code", data={"email": email})

        # Get the code
        login_code = test_db.query(EmailLoginCode).filter(
            EmailLoginCode.email == email,
            EmailLoginCode.used == False
        ).first()

        # Make 5 wrong attempts (using wrong codes)
        for i in range(5):
            response = client.post(
                "/auth/verify-code",
                data={"email": email, "code": str(i).zfill(6)}
            )
            if response.status_code == 429:
                break

        # 6th attempt should be locked
        response = client.post(
            "/auth/verify-code",
            data={"email": email, "code": "999999"}
        )
        assert response.status_code == 429
        assert "验证次数过多" in response.json()["detail"]

    def test_verify_code_creates_user_if_not_exists(self, client: TestClient, test_db: Session):
        """Verify code should auto-create user if not exists."""
        email = "newuser@example.com"

        # Ensure user doesn't exist
        existing = test_db.query(User).filter(User.email == email).first()
        assert existing is None

        # Send and verify code
        client.post("/auth/send-code", data={"email": email})
        login_code = test_db.query(EmailLoginCode).filter(
            EmailLoginCode.email == email
        ).first()

        response = client.post(
            "/auth/verify-code",
            data={"email": email, "code": login_code.code},
            follow_redirects=False
        )
        # Should get redirect to dashboard
        assert response.status_code == 302

        # User should be created
        user = test_db.query(User).filter(User.email == email).first()
        assert user is not None


class TestLogout:
    """Tests for /auth/logout endpoint."""

    def test_logout_clears_session(self, client: TestClient, valid_session_cookie: str):
        """Logout should clear session cookie and redirect to login."""
        # Access with valid session - don't follow redirect
        response = client.post(
            "/auth/logout",
            cookies={"session": valid_session_cookie},
            follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

        # Session cookie should be cleared (empty or deleted)
        assert response.cookies.get("session") in ("", None) or "session" not in response.cookies


class TestLoginPage:
    """Tests for /auth/login GET endpoint."""

    def test_login_page_returns_html(self, client: TestClient):
        """Login page should return HTML."""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
