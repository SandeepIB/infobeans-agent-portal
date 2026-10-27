# Backend — NOW

## Purpose

FastAPI backend serving the v2 API. Legacy routes remain in `app.py` (frozen).

## Stack

- Python 3.11+
- FastAPI
- SQLite (Phase 1) / PostgreSQL (production)
- Uvicorn

## Mounting v2 Routers

The only permitted change to `app.py` is adding `include_router(...)` calls:

```python
# app.py — only add include_router lines, nothing else
from api.review import router as review_router
from api.prompts import router as prompts_router

app.include_router(review_router, prefix="/api/v2")
app.include_router(prompts_router, prefix="/api/v2")
```

## v2 API Routers

| File | Prefix | Purpose |
|------|--------|---------|
| `api/review.py` | `/api/v2/review` | Submit reviews, upload PPTs, get results |
| `api/prompts.py` | `/api/v2/prompts` | Prompt CRUD and activation |
| `api/rules.py` | `/api/v2/rules` | Rule Library management |
| `api/agents.py` | `/api/v2/agents` | Agent Registry view |
| `api/observability.py` | `/api/v2/observability` | Dashboards and metrics |
| `api/health.py` | `/api/v2/health` | Health check |

## Health Check

```
GET /api/v2/health
```

Response:

```json
{
  "status": "ok",
  "provider": "gateway",
  "provider_healthy": true,
  "db_connected": true,
  "libreoffice_available": false,
  "langsmith_enabled": true,
  "trulens_enabled": true
}
```

## API Conventions

- Request/response models as Pydantic dataclasses
- Consistent error format: `{"error": "...", "code": "..."}`
- Pagination on list endpoints: `?page=1&per_page=20`
- Version prefix: all new endpoints at `/api/v2/`
- Authentication: JWT or session token (configured at deployment)

## Dependency Injection

Use FastAPI dependency injection for services:

```python
from fastapi import Depends

def get_review_service(db=Depends(get_db)) -> ReviewService:
    return ReviewService(db=db)

@router.post("/review/start")
async def start_review(
    request: ReviewRequest,
    review_service: ReviewService = Depends(get_review_service),
):
    ...
```

## Related Documents

- See: [frontend.md](frontend.md) for frontend-to-API communication
- See: [database.md](database.md) for DB conventions
- See: [../architecture/01-system-overview.md](../architecture/01-system-overview.md) for directory map
