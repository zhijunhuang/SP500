"""
Acceptance tests for billing pages.

Tests:
- /billing/subscribe requires login
- /billing/success and /billing/cancel pages load
- create-checkout-session with mocked Stripe
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User


class TestBillingPages:
    """Tests for billing pages."""

    def test_subscribe_page_requires_login(self, client: TestClient):
        """Subscribe page should redirect to login if not authenticated."""
        response = client.get("/billing/subscribe")
        assert response.status_code == 401

    def test_subscribe_page_loads_with_session(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user: User
    ):
        """Subscribe page should load for authenticated user."""
        response = client.get(
            "/billing/subscribe",
            cookies={"session": valid_session_cookie}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_success_page_loads(self, client: TestClient):
        """Success page should load without auth."""
        response = client.get("/billing/success")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_cancel_page_loads(self, client: TestClient):
        """Cancel page should load without auth."""
        response = client.get("/billing/cancel")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestCreateCheckoutSession:
    """Tests for /billing/create-checkout-session endpoint."""

    def test_create_checkout_requires_login(self, client: TestClient):
        """Create checkout session should require authentication."""
        response = client.post("/billing/create-checkout-session")
        assert response.status_code == 401

    def test_create_checkout_with_mocked_stripe(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user: User
    ):
        """Create checkout session should work with mocked Stripe."""
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"

        with patch("app.routers.billing.stripe.Customer") as MockCustomer, \
             patch("app.routers.billing.stripe.checkout.Session") as MockCheckout:

            MockCustomer.create.return_value = mock_customer
            MockCheckout.create.return_value = mock_session

            # User already has stripe_customer_id set by fixture
            sample_user.stripe_customer_id = "cus_existing123"

            response = client.post(
                "/billing/create-checkout-session",
                cookies={"session": valid_session_cookie}
            )

            assert response.status_code == 200
            assert response.json()["url"] == "https://checkout.stripe.com/test"

    def test_create_checkout_creates_customer_if_missing(
        self,
        client: TestClient,
        valid_session_cookie: str,
        sample_user: User,
        test_db: Session
    ):
        """Create checkout session should create Stripe customer if missing."""
        sample_user.stripe_customer_id = None  # Ensure no customer ID

        mock_customer = MagicMock()
        mock_customer.id = "cus_newly_created"

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"

        with patch("app.routers.billing.stripe.Customer") as MockCustomer, \
             patch("app.routers.billing.stripe.checkout.Session") as MockCheckout:

            MockCustomer.create.return_value = mock_customer
            MockCheckout.create.return_value = mock_session

            response = client.post(
                "/billing/create-checkout-session",
                cookies={"session": valid_session_cookie}
            )

            assert response.status_code == 200
            # Verify customer was created
            assert MockCustomer.create.called
            test_db.refresh(sample_user)
            assert sample_user.stripe_customer_id == "cus_newly_created"
