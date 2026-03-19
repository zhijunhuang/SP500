"""
pytest fixtures for SP500 acceptance tests.

Uses httpx.TestClient to test FastAPI routes directly without starting a real server.
"""
import os
import hashlib
import secrets
from datetime import date, datetime, timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["STRIPE_API_KEY"] = "sk_test_mock"
os.environ["STRIPE_PRICE_ID"] = "price_mock"
os.environ["SMTP_HOST"] = ""
os.environ["BASE_URL"] = "http://localhost:8000"

from app.main import create_app
from app.utils.db import Base, get_db
from app.models import User, APIToken, SP500Constituent, SP500Meta, EmailLoginCode


# Test database engine (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override get_db dependency for tests."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db() -> Generator[Session, None, None]:
    """Create fresh database tables for each test, then clean up."""
    # Import models to register them with Base.metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=test_engine)

    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient with overridden database dependency."""
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    # Use the same test_db session across the app
    def _get_test_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db

    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_user(test_db: Session) -> User:
    """Create a test user with active subscription."""
    user = User(
        email="test@example.com",
        subscription_status="active",
        stripe_customer_id="cus_test123"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_expired_user(test_db: Session) -> User:
    """Create a test user with expired subscription."""
    user = User(
        email="expired@example.com",
        subscription_status="expired",
        stripe_customer_id="cus_expired123"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_api_token(test_db: Session, sample_user: User) -> tuple[str, APIToken]:
    """Create a test API token. Returns (plain_token, token_object)."""
    plain_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()

    api_token = APIToken(
        user_id=sample_user.id,
        name="Test Token",
        token_hash=token_hash,
        revoked=False
    )
    test_db.add(api_token)
    test_db.commit()
    test_db.refresh(api_token)
    return plain_token, api_token


@pytest.fixture
def sample_constituents(test_db: Session) -> list[SP500Constituent]:
    """Create S&P 500 constituent test data including historical data."""
    constituents = [
        # Currently active constituents
        SP500Constituent(
            code="AAPL",
            company_name="Apple Inc.",
            sector="Information Technology",
            industry="Technology Hardware",
            effective_from=date(2020, 1, 1),
            effective_to=None
        ),
        SP500Constituent(
            code="MSFT",
            company_name="Microsoft Corporation",
            sector="Information Technology",
            industry="Software",
            effective_from=date(2020, 1, 1),
            effective_to=None
        ),
        SP500Constituent(
            code="GOOGL",
            company_name="Alphabet Inc.",
            sector="Communication Services",
            industry="Interactive Media",
            effective_from=date(2020, 1, 1),
            effective_to=None
        ),
        # IBM - added in 2020, removed in 2024
        SP500Constituent(
            code="IBM",
            company_name="International Business Machines",
            sector="Information Technology",
            industry="IT Services",
            effective_from=date(2020, 1, 1),
            effective_to=date(2024, 6, 1)
        ),
        # Tesla - added in 2020, still active
        SP500Constituent(
            code="TSLA",
            company_name="Tesla Inc.",
            sector="Consumer Discretionary",
            industry="Automobiles",
            effective_from=date(2020, 12, 21),
            effective_to=None
        ),
    ]

    for c in constituents:
        test_db.add(c)
    test_db.commit()

    for c in constituents:
        test_db.refresh(c)

    return constituents


@pytest.fixture
def sample_meta(test_db: Session) -> SP500Meta:
    """Create sample metadata."""
    meta = SP500Meta(
        key="data_source",
        value="Wikipedia - List of S&P 500 companies"
    )
    test_db.add(meta)
    test_db.commit()
    test_db.refresh(meta)
    return meta


@pytest.fixture
def valid_session_cookie(client: TestClient, sample_user: User, test_db: Session) -> str:
    """Create a valid session cookie for the sample user by completing the login flow."""
    # Send verification code
    client.post("/auth/send-code", data={"email": sample_user.email})

    # Get the generated code
    login_code = test_db.query(EmailLoginCode).filter(
        EmailLoginCode.email == sample_user.email,
        EmailLoginCode.used == False
    ).first()

    # Verify with correct code - don't follow redirect to capture the cookie
    response = client.post(
        "/auth/verify-code",
        data={"email": sample_user.email, "code": login_code.code},
        follow_redirects=False
    )

    # Should get 302 redirect with session cookie
    assert response.status_code == 302, f"Expected 302, got {response.status_code}: {response.text}"
    assert "session" in response.cookies, f"No session cookie in response. Cookies: {dict(response.cookies)}"
    return response.cookies["session"]
