#!/bin/bash

# Kill uvicorn process running the app
pkill -f "uvicorn app.main:app" 2>/dev/null || true

echo "Stopped"
