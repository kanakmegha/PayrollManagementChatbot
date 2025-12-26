#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "--- Upgrading Pip ---"
python -m pip install --upgrade pip

echo "--- Installing All Requirements ---"
# We install everything first
pip install --no-cache-dir -r requirements.txt

echo "--- FORCE FIX: Downgrading HTTPX ---"
# We do this LAST to make sure nothing else upgrades it back to 0.28.0
pip uninstall -y httpx
pip install "httpx==0.27.2"

echo "--- VERIFYING VERSION ---"
python -c "import httpx; print(f'VERIFIED HTTPX VERSION: {httpx.__version__}')"