#!/usr/bin/env bash
set -o errexit

echo "--- Pre-Flight Check ---"
# This confirms which httpx the STARTUP environment is actually seeing
python -c "import httpx; print(f'STARTUP HTTPX VERSION: {httpx.__version__}')"

echo "--- Starting Uvicorn Server ---"
PORT=${PORT:-10000}
python -m uvicorn main:app --host 0.0.0.0 --port $PORT