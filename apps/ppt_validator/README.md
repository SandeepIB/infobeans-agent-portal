# InfoBeans Agentic PPT Review Platform

A PowerPoint quality gate that evaluates customer-facing presentations for brand compliance,
content quality, storytelling, proposal coverage, and executive readiness.

---

## Requirements

| Dependency | Version | Notes |
|-----------|---------|-------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend dev server and build |
| npm | 8+ | Frontend package manager |
| LibreOffice | any | Optional — enables slide-to-image rendering |

---

## Quick Start

```bash
# 1. Clone / navigate to the project directory
cd Ib-ppt-validator

# 2. Copy environment config and fill in your keys
cp .env.example .env
# Edit .env — set LLM_PROVIDER and the matching API key

# 3. Start everything (backend + frontend)
bash start.sh
```

Open **http://localhost:5173** in your browser.

---

## Installation (step by step)

### 1. Python environment

```bash
# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment configuration

```bash
cp .env.example .env
```

Open `.env` and set the required values:

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | One of: `gateway` `claude` `groq` `gemini` `openai` `litellm` `mock` |
| `GATEWAY_API_KEY` | If using `gateway` | InfoBeans gateway key |
| `ANTHROPIC_API_KEY` | If using `claude` | Anthropic API key |
| `GROQ_API_KEY` | If using `groq` | Groq API key |
| `GEMINI_API_KEY` | If using `gemini` | Google Gemini API key |
| `OPENAI_API_KEY` | If using `openai` | OpenAI API key |
| `DATABASE_URL` | No | Defaults to `sqlite:///platform.db` |

### 3. Database setup

```bash
python db/migrate.py
# Or via start script:
bash start.sh migrate
```

### 4. Frontend

```bash
cd frontend
npm install
npm run build       # production build → frontend/dist/
# or
npm run dev         # dev server on http://localhost:5173
```

---

## Running the application

### Start script (recommended)

```bash
bash start.sh            # start backend + frontend
bash start.sh backend    # backend API only
bash start.sh frontend   # frontend dev server only
bash start.sh migrate    # run DB migrations only
bash start.sh --help     # show usage
```

### Manual commands

```bash
# Backend (port 8000)
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Frontend dev server (port 5173, proxies /api to backend)
cd frontend && npm run dev

# Run tests
pytest tests/                    # all tests (MockProvider, no real LLM)
pytest tests/unit/               # unit tests only
pytest tests/integration/        # integration tests only
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/health` | GET | Platform health + LLM provider status |
| `/api/v2/review` | POST | Upload PPTX, run review pipeline |
| `/api/v2/review/{run_id}` | GET | Get review result by run ID |
| `/api/v2/review` | GET | List recent review runs |
| `/api/v2/agents` | GET | List registered agents |
| `/api/v2/prompts/{agent_id}` | GET | List prompt versions for agent |
| `/api/v2/prompts/{agent_id}/active` | GET | Get active prompt |
| `/api/v2/rules/{domain}` | GET | Get rules for domain |
| `/api/v2/observability/cost/{run_id}` | GET | Cost summary for a run |
| `/docs` | GET | Interactive Swagger UI |

### Review request example

```bash
curl -X POST http://localhost:8000/api/v2/review \
  -F "file=@my_deck.pptx" \
  -F 'profile={"review_profile":"customer_presentation"}'
```

Response:
```json
{
  "run_id": "...",
  "status": "ready",
  "score": 84,
  "agent_results": [...],
  "cost": {"input_tokens": 1200, "output_tokens": 400, "cost_usd": 0.012}
}
```

---

## Project Structure

```
app.py               Entry point — legacy routes + v2 router mounts
db.py                Legacy DB access (runs table)
rules.yaml           Legacy rule set (frozen)
correct_pptx.py      Legacy PPTX correction (frozen)
static/index.html    Legacy UI (frozen)

agents/              ReviewAgent ABC + all agent implementations
  base.py            AgentContract, Finding, ActionType, Severity
  branding_agent.py  Rule-based brand compliance
  content_agent.py   LLM-based content quality
  story_agent.py     LLM-based storytelling
  ...

llm/                 LLMProvider abstraction layer
  provider.py        LLMProvider ABC + ProviderFactory
  providers/         gateway, claude, groq, gemini, openai, litellm, mock

services/            Business logic
  review_service.py  Orchestrator — DAG execution
  prompt_service.py  Prompt version management
  rule_service.py    Rule library access
  ppt_service.py     PPTX extraction (never sends raw XML to LLM)
  cost_governance_service.py  Token + cost budget enforcement
  cache_service.py   LLM response caching

api/                 FastAPI v2 routers
  review.py  health.py  prompts.py  rules.py  agents.py  observability.py

db/                  Database layer
  migrate.py         Migration runner (additive, idempotent)
  session.py         SQLite connection factory
  migrations/        SQL migration files

prompts/             Seed prompt YAML/JSON files (loaded into DB on first run)
rule_library/        Versioned rule definitions (branding, template, typography, ...)
renderer/            Slide → PNG renderer (LibreOffice or fallback stub)
frontend/            React + Vite UI
tests/               Pytest test suite (MockProvider only — no real LLM calls)
```

---

## LLM Providers

Select provider via `LLM_PROVIDER` in `.env`:

| Value | Provider | Notes |
|-------|----------|-------|
| `gateway` | InfoBeans Gateway | Default — recommended for production |
| `claude` | Anthropic Claude | Direct API |
| `groq` | Groq | Fast inference |
| `gemini` | Google Gemini | Direct API |
| `openai` | OpenAI | Direct API |
| `litellm` | LiteLLM proxy | Routes to any model |
| `mock` | Mock (test only) | Deterministic, no network calls |

---

## Testing

```bash
# Unit tests — always use MockProvider (fast, no LLM calls)
pytest tests/unit/ -v

# Integration tests — uses test DB + MockProvider
pytest tests/integration/ -v

# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=term-missing
```

**Rule:** Never set `LLM_PROVIDER` to anything other than `mock` in tests.

---

## Optional: LibreOffice (slide rendering)

LibreOffice enables the Visual Agent to render slides as images for design checking.
Without it, the Visual Agent is skipped and all other agents run normally.

```bash
sudo apt-get install libreoffice    # Ubuntu/Debian
brew install --cask libreoffice     # macOS
```

---

## Health check

```bash
curl http://localhost:8000/api/v2/health
# {"status": "ok"}

curl http://localhost:8000/api/v2/health/llm
# {"status": "ok", "provider": "GatewayProvider"}
```

---

## Production deployment

```bash
# Build frontend
cd frontend && npm run build
cd ..

# Run backend (serve frontend/dist via /app mount)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
```

For production, use PostgreSQL (`DATABASE_URL=postgresql://...`),
run behind nginx with TLS, and set `LANGSMITH_REDACT_PII=true`.

See [docs/operations/deployment.md](docs/operations/deployment.md) for full deployment guide.
