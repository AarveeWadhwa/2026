#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! python3 -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
  echo "Installing required Python packages..."
  python3 -m pip install -r requirements.txt
fi
echo "Starting BidPilot AI at http://127.0.0.1:8000"
python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
