#!/usr/bin/env bash
# Development start script — NOT for production.
# For production use the systemd service in config/infobeans-agent-hub.service.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f .env ]]; then
  echo "ERROR: .env file not found. Copy .env.example and fill in your values." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "ERROR: .venv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

# Run pending migrations
echo "Running Alembic migrations..."
.venv/bin/alembic upgrade head

echo "Starting InfoBeans Agent Hub on http://127.0.0.1:8000 ..."
exec .venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload \
  --log-level info
