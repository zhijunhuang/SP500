#!/bin/bash
set -e

export DATABASE_URL="mysql+mysqlconnector://admin:passw0rd@localhost:3306/sp500_test?charset=utf8mb4"
export SECRET_KEY="test-secret-key-for-testing-only"
export STRIPE_API_KEY="sk_test_mock"
export SMTP_HOST=""
export BASE_URL="http://localhost:8000"

echo "Starting SP500 service on 127.0.0.1:8000..."
uvicorn app.main:app --host 127.0.0.1 --port 8000
