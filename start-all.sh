#!/usr/bin/env bash
# Start all InfoBeans Agent Hub services (development / manual restart)
# For production use the systemd service in config/infobeans-agent-hub.service
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── PPT Validator (port 8001) ─────────────────────────────────────────────
echo "[ppt-validator] Starting on :8001 ..."
cd "$REPO/apps/ppt_validator"
nohup python3 -m uvicorn app:app --host 127.0.0.1 --port 8001 \
  > /tmp/ppt-validator.log 2>&1 &
PPT_PID=$!
disown $PPT_PID
echo "[ppt-validator] PID $PPT_PID"

sleep 3

# ── Agent Hub (port 8000) ─────────────────────────────────────────────────
echo "[hub] Starting on :8000 ..."
cd "$REPO"
nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  > /tmp/hub.log 2>&1 &
HUB_PID=$!
disown $HUB_PID
echo "[hub] PID $HUB_PID"

sleep 3

echo ""
echo "=== Status ==="
curl -s -o /dev/null -w "Hub          https://agenthub.creatingwow.in → HTTP %{http_code}\n" http://127.0.0.1:8000/
curl -s -o /dev/null -w "PPT Validator http://127.0.0.1:8001          → HTTP %{http_code}\n" http://127.0.0.1:8001/
echo ""
echo "Logs: /tmp/hub.log | /tmp/ppt-validator.log"
