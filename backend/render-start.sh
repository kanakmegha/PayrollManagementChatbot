#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "--- Starting Uvicorn Server ---"

# Render provides the $PORT environment variable automatically.
# We must use 0.0.0.0 to allow external traffic.
python -m uvicorn main:app --host 0.0.0.0 --port $PORT