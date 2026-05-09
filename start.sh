#!/bin/bash
set -e

# 不设置 DATABASE_URL，使用 app/config/db.py 中的配置 (sp500)
export SECRET_KEY="your-secret-key-here-change-in-production"
export STRIPE_API_KEY="sk_test_..."
export SMTP_HOST=""
export BASE_URL="http://localhost:8000"

echo "Starting SP500 service on 127.0.0.1:8000..."
uvicorn app.main:app --host 127.0.0.1 --port 8000
