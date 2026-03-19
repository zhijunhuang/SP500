#!/bin/bash
set -e

echo "Installing test dependencies..."
pip install pytest pytest-asyncio pytest-cov httpx -q

echo "Creating test database..."
mysql -u admin -ppassw0rd -e "CREATE DATABASE IF NOT EXISTS sp500_test;" 2>/dev/null || echo "MySQL not available, tests will use SQLite"

echo "Build complete"
