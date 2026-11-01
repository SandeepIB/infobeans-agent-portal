#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  InfoBeans Agent Hub — Local Development Start Script
#
#  Usage:
#    bash start-all-local.sh              # normal mode
#    bash start-all-local.sh --debug      # debug log level + hot-reload
#    bash start-all-local.sh --logs       # start then tail logs live
#    bash start-all-local.sh --debug --logs
#
#  What it does:
#    1. Validates .venv and .env exist
#    2. Checks /etc/hosts entry and warns if wrong
#    3. Runs Alembic migrations
#    4. Kills any process already on ports 8000 / 8001
#    5. Starts PPT Validator  on 0.0.0.0:8001  (log → /tmp/ppt-validator.log)
#    6. Starts Agent Hub      on 0.0.0.0:8000  (log → /tmp/hub.log)
#    7. Reloads Docker nginx so it picks up the latest config
#    8. Verifies both services respond HTTP 200
#
#  Auto-restart on system reboot:
#    Install the systemd user services instead — see SERVER_SETUP.md § Local Development
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_GATEWAY="172.26.0.1"   # host IP as seen from inside the Docker nginx container
DOCKER_NET="docker-local_tid-local"

# ── Flags ─────────────────────────────────────────────────────────────────────
DEBUG=false
FOLLOW_LOGS=false
for arg in "${@:-}"; do
  case "$arg" in
    --debug|-d) DEBUG=true  ;;
    --logs|-l)  FOLLOW_LOGS=true ;;
    --help|-h)
      sed -n '/^#  Usage:/,/^[^#]/p' "$0" | grep '^#' | sed 's/^# \{0,2\}//'
      exit 0 ;;
  esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  [OK]${NC}   $*"; }
info() { echo -e "${CYAN}  [-->]${NC}  $*"; }
warn() { echo -e "${YELLOW}  [!]${NC}   $*"; }
fail() { echo -e "${RED}  [ERR]${NC} $*" >&2; exit 1; }
hr()   { echo -e "${BOLD}──────────────────────────────────────────────────${NC}"; }

# ── Port helper ───────────────────────────────────────────────────────────────
free_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Port $port busy (PID $pids) — stopping..."
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
    ok "Port $port freed."
  fi
}

# ── Header ────────────────────────────────────────────────────────────────────
hr
if $DEBUG; then
  echo -e "${BOLD}InfoBeans Agent Hub — Local Start  [DEBUG MODE]${NC}"
else
  echo -e "${BOLD}InfoBeans Agent Hub — Local Start${NC}"
fi
hr

# ── Pre-flight ────────────────────────────────────────────────────────────────
[[ -d "$REPO/.venv" ]] || fail ".venv not found. Run:\n  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
[[ -f "$REPO/.env" ]] || fail ".env not found. Copy .env.example and fill in values."
ok "Virtual env and .env found."

# Hosts file check
HOSTS_ENTRY=$(grep -E 'agenthub\.creatingwow\.in' /etc/hosts 2>/dev/null || true)
if [[ -z "$HOSTS_ENTRY" ]]; then
  warn "/etc/hosts has no entry for agenthub.creatingwow.in"
  warn "Fix: echo '127.0.0.1 agenthub.creatingwow.in' | sudo tee -a /etc/hosts"
elif ! echo "$HOSTS_ENTRY" | grep -q '127\.0\.0\.1'; then
  WRONG_IP=$(echo "$HOSTS_ENTRY" | awk '{print $1}' | head -1)
  warn "/etc/hosts points to $WRONG_IP (unreachable). Fix:"
  warn "sudo sed -i 's/${WRONG_IP}.*agenthub.creatingwow.in/127.0.0.1 agenthub.creatingwow.in/' /etc/hosts"
else
  ok "/etc/hosts: agenthub.creatingwow.in → 127.0.0.1"
fi

# ── Migrations ────────────────────────────────────────────────────────────────
info "Running Alembic migrations..."
cd "$REPO"
"$REPO/.venv/bin/alembic" upgrade head 2>&1 | grep -v '^$' | tail -5
ok "Migrations complete."

# ── Free ports ────────────────────────────────────────────────────────────────
free_port 8000
free_port 8001

# ── Log level ─────────────────────────────────────────────────────────────────
if $DEBUG; then
  LOG_LEVEL="debug"
  RELOAD="--reload"
  info "Debug mode: log-level=debug, hot-reload=on"
else
  LOG_LEVEL="info"
  RELOAD="--reload"   # keep reload on in local dev regardless
fi

# ── Start PPT Validator (port 8001) ───────────────────────────────────────────
info "Starting PPT Validator on :8001 ..."
cd "$REPO/apps/ppt_validator"
# shellcheck disable=SC2086
nohup python3 -m uvicorn app:app \
  --host 0.0.0.0 \
  --port 8001 \
  --log-level "$LOG_LEVEL" \
  $RELOAD \
  > /tmp/ppt-validator.log 2>&1 &
PPT_PID=$!
disown $PPT_PID
ok "PPT Validator started (PID $PPT_PID)."

# ── Start Agent Hub (port 8000) ───────────────────────────────────────────────
info "Starting Agent Hub on :8000 ..."
cd "$REPO"
# Bind to 0.0.0.0 so the Docker nginx container (at 172.26.0.1) can reach the host.
# See config/nginx.conf: proxy_pass http://172.26.0.1:8000
# shellcheck disable=SC2086
nohup .venv/bin/python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level "$LOG_LEVEL" \
  $RELOAD \
  > /tmp/hub.log 2>&1 &
HUB_PID=$!
disown $HUB_PID
ok "Agent Hub started (PID $HUB_PID)."

# ── Reload Docker nginx ───────────────────────────────────────────────────────
# The nginx serving agenthub.creatingwow.in runs inside a Docker container.
# Reload it so it picks up any config changes and clears cached upstream state.
DOCKER_CONTAINER=$(docker ps -qf "network=${DOCKER_NET}" 2>/dev/null | head -1 || true)
if [[ -n "$DOCKER_CONTAINER" ]]; then
  info "Reloading nginx in Docker container ($DOCKER_CONTAINER)..."
  if docker exec "$DOCKER_CONTAINER" nginx -s reload 2>/dev/null; then
    ok "Docker nginx reloaded."
  else
    warn "nginx reload returned non-zero (non-fatal — may already be current)."
  fi
else
  warn "Docker container on network '$DOCKER_NET' not found — skipping nginx reload."
  warn "If nginx is not serving the site, run: docker exec <container_id> nginx -s reload"
fi

# ── Wait and verify ───────────────────────────────────────────────────────────
info "Waiting for services to be ready..."
sleep 5

hr
echo -e "${BOLD}Status${NC}"

HTTP_HUB=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null || echo "000")
HTTP_PPT=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/ 2>/dev/null || echo "000")

[[ "$HTTP_HUB" == "200" ]] \
  && ok "Hub          http://127.0.0.1:8000   → HTTP $HTTP_HUB" \
  || warn "Hub          http://127.0.0.1:8000   → HTTP $HTTP_HUB  (check /tmp/hub.log)"

[[ "$HTTP_PPT" == "200" ]] \
  && ok "PPT Validator http://127.0.0.1:8001  → HTTP $HTTP_PPT" \
  || warn "PPT Validator http://127.0.0.1:8001  → HTTP $HTTP_PPT  (check /tmp/ppt-validator.log)"

echo ""
echo -e "  Site URL:    ${CYAN}https://agenthub.creatingwow.in/${NC}"
echo -e "  Hub logs:    ${CYAN}tail -f /tmp/hub.log${NC}"
echo -e "  PPT logs:    ${CYAN}tail -f /tmp/ppt-validator.log${NC}"
echo -e "  Stop all:    ${CYAN}kill \$(lsof -ti :8000 :8001 2>/dev/null)${NC}"
if $DEBUG; then
  echo ""
  echo -e "  ${YELLOW}DEBUG mode — hot-reload active. File changes restart the server automatically.${NC}"
fi
hr

# ── Follow logs (optional) ────────────────────────────────────────────────────
if $FOLLOW_LOGS; then
  echo ""
  echo -e "${CYAN}Following logs (Ctrl+C stops tailing — apps keep running in background)...${NC}"
  echo ""
  trap 'echo ""; echo "Log tail stopped. Apps are still running in the background."' INT TERM
  tail -f /tmp/hub.log /tmp/ppt-validator.log
fi
