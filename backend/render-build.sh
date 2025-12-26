#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "--- Upgrading Pip ---"
python -m pip install --upgrade pip

echo "--- Fixing HTTPX/Supabase Proxy Conflict ---"
# Force remove any cached/pre-installed version that causes the 'proxy' error
pip uninstall -y httpx
pip install "httpx==0.27.2"

echo "--- Installing Requirements ---"
# Use --no-cache-dir to ensure we get a fresh, clean install
pip install --no-cache-dir -r requirements.txt

echo "--- Build Script Finished ---"