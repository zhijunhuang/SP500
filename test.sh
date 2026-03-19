#!/bin/bash
set -e

export DATABASE_URL="sqlite:///:memory:"
export SECRET_KEY="test-secret-key-for-testing-only"
export STRIPE_API_KEY="sk_test_mock"
export STRIPE_PRICE_ID="price_mock"
export SMTP_HOST=""
export BASE_URL="http://localhost:8000"

echo "Running acceptance tests..."
pytest tests/ -v --tb=short
