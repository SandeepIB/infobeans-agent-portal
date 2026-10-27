# Deployment

## Purpose

Document how to deploy the platform in Phase 1 (single-instance) and future configurations.

## Phase 1 — Single Instance

```
Linux server
├── Python 3.11+
├── uvicorn (backend)
├── Node.js / npm (frontend build)
├── LibreOffice (optional — for slide rendering)
├── SQLite (platform DB)
├── SQLite (TruLens eval DB — separate)
└── .env (secrets, never committed)
```

## Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Build frontend
cd frontend && npm run build

# Run DB migrations (idempotent)
python db/migrate.py

# Start backend
uvicorn app:app --host 0.0.0.0 --port 8000

# Start frontend dev server (development only)
cd frontend && npm run dev
```

## Environment Configuration

Copy `.env.example` to `.env` and fill in all required values:

```bash
cp .env.example .env
# Edit .env — set LLM provider keys, DB config, observability keys
```

Never commit `.env`. It is in `.gitignore`.

## Health Check

```bash
curl http://localhost:8000/api/v2/health
```

Response includes:
- Platform status
- Active LLM provider + health check result
- DB connection status
- LibreOffice availability

## LibreOffice (Optional)

LibreOffice enables slide-to-image rendering for the Visual Agent. If absent:
- `UnavailableRenderer` is used
- Visual Agent emits a single INFO finding
- All other agents run normally

Install: `sudo apt-get install libreoffice`

## Production Considerations

- Use PostgreSQL instead of SQLite (`DATABASE_URL` env var)
- Run behind a reverse proxy (nginx) with TLS
- Set `LANGSMITH_REDACT_PII=true` for customer data environments
- Configure daily/monthly cost budgets in `.env`
- Set up log rotation for application logs

## Related Documents

- See: [security.md](security.md) for secrets and access control
- See: [../development/database.md](../development/database.md) for migration details
- See: [../architecture/12-scalability.md](../architecture/12-scalability.md) for future scale
