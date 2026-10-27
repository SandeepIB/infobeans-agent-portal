#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  InfoBeans Agentic PPT Review Platform — Start Script
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ── Network Configuration ─────────────────────────────────────────────────────
SERVER_IP="${SERVER_IP:-$(hostname -I | awk '{print $1}')}"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Mode ──────────────────────────────────────────────────────────────────────
MODE="${1:-all}"   # all | backend | frontend | migrate

usage() {
  echo ""
  echo "Usage: $0 [all|backend|frontend|migrate]"
  echo ""
  echo "  all       Start backend + frontend dev server (default)"
  echo "  backend   Start backend API only (port \${APP_PORT:-8080})"
  echo "  frontend  Start frontend dev server only (port ${FRONTEND_PORT:-5173})"
  echo "  migrate   Run DB migrations only and exit"
  echo ""
}

# ── Pre-flight checks ─────────────────────────────────────────────────────────
check_python() {
  if ! command -v python3 &>/dev/null; then
    error "Python 3.11+ is required but not found."
  fi
  PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  info "Python $PY_VER found."
}

check_node() {
  if ! command -v node &>/dev/null; then
    warn "Node.js not found — frontend dev server will not start."
    return 1
  fi
  info "Node $(node --version) found."
  return 0
}

check_env() {
  if [ ! -f ".env" ]; then
    warn ".env not found. Copying from .env.example..."
    cp .env.example .env
    warn "Edit .env and fill in your LLM API keys before running."
  fi
}

check_pip_deps() {
  info "Checking Python dependencies..."
  if ! python3 -c "import fastapi" &>/dev/null; then
    info "Installing Python dependencies..."
    pip install -r requirements.txt -q || error "pip install failed."
  fi
  success "Python dependencies OK."
}

check_npm_deps() {
  if [ ! -d "frontend/node_modules" ]; then
    info "Installing frontend dependencies..."
    (cd frontend && npm install --silent) || error "npm install failed."
  fi
  success "Frontend dependencies OK."
}

# ── Migrations ────────────────────────────────────────────────────────────────
run_migrations() {
  info "Running DB migrations..."
  python3 -c "from db.migrate import run; run()" && success "Migrations complete."
}

# ── Port helpers ──────────────────────────────────────────────────────────────
free_port() {
  local port="$1"
  local pids
  pids=$(lsof -ti :"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    warn "Port $port in use — killing existing process(es): $pids"
    echo "$pids" | xargs -r kill -9 2>/dev/null || true
    sleep 1
    success "Port $port freed."
  fi
}

wait_for_backend() {
  local port="${1:-8080}"
  local retries=30
  info "Waiting for backend to be ready on port $port ..."
  for i in $(seq 1 $retries); do
    if curl -sf "http://127.0.0.1:${port}/docs" -o /dev/null 2>/dev/null || \
       curl -sf "http://127.0.0.1:${port}/"     -o /dev/null 2>/dev/null; then
      success "Backend is ready."
      return 0
    fi
    sleep 1
  done
  warn "Backend did not respond after ${retries}s — frontend may proxy errors on first request."
}


# ── Start functions ───────────────────────────────────────────────────────────
start_backend() {
  PORT="${APP_PORT:-8080}"
  free_port "$PORT"

  info "Starting backend on http://${SERVER_IP}:${PORT} ..."
  exec uvicorn app:app --host 0.0.0.0 --port "$PORT" --reload
}

start_frontend() {
  FPORT="${FRONTEND_PORT:-5173}"

  info "Starting frontend dev server on http://${SERVER_IP}:${FPORT} ..."
  exec npm run dev --prefix frontend -- --host 0.0.0.0
}

start_all() {
  PORT="${APP_PORT:-8080}"
  FPORT="${FRONTEND_PORT:-5173}"

  free_port "$PORT"
  free_port "$FPORT"

  # Run backend in background
  info "Starting backend on http://${SERVER_IP}:${PORT} ..."
  uvicorn app:app --host 0.0.0.0 --port "$PORT" --reload &
  BACKEND_PID=$!

  # Wait for backend to accept connections before starting the proxy (Vite)
  wait_for_backend "$PORT"

  # Run frontend in background
  info "Starting frontend dev server on http://${SERVER_IP}:${FPORT} ..."
  (cd frontend && npm run dev -- --host 0.0.0.0) &
  FRONTEND_PID=$!

  echo ""
  success "Platform started:"
  echo -e "  Backend API:  ${CYAN}http://${SERVER_IP}:${PORT}${NC}"
  echo -e "  Frontend UI:  ${CYAN}http://${SERVER_IP}:${FPORT}${NC}"
  echo -e "  API docs:     ${CYAN}http://${SERVER_IP}:${PORT}/docs${NC}"
  echo ""
  echo "  Access the application from another machine using:"
  echo -e "  ${CYAN}http://${SERVER_IP}:${FPORT}${NC}"
  echo ""
  echo "  Press Ctrl+C to stop all processes."
  echo ""

  # Wait and forward signals
  trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
  wait $BACKEND_PID $FRONTEND_PID
}

# ── Main ──────────────────────────────────────────────────────────────────────
case "$MODE" in
  -h|--help|help) usage; exit 0 ;;
  migrate)
    check_python
    check_env
    check_pip_deps
    run_migrations
    ;;
  backend)
    check_python
    check_env
    check_pip_deps
    run_migrations
    start_backend
    ;;
  frontend)
    check_node || error "Node.js is required for frontend mode."
    check_npm_deps
    start_frontend
    ;;
  all)
    check_python
    check_env
    check_pip_deps
    check_node && check_npm_deps || warn "Skipping frontend — Node.js not found."
    run_migrations
    if check_node &>/dev/null; then
      start_all
    else
      start_backend
    fi
    ;;
  *)
    error "Unknown mode: $MODE"
    usage
    ;;
esac
