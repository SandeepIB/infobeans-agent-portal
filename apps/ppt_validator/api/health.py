"""Health API — liveness and LLM provider health."""
from fastapi import APIRouter
from llm.provider import ProviderFactory

router = APIRouter(prefix="/api/v2/health", tags=["health"])


@router.get("")
def health():
    return {"status": "ok"}


@router.get("/llm")
def llm_health():
    try:
        provider = ProviderFactory.from_env()
        ok = provider.health()
        return {"status": "ok" if ok else "degraded", "provider": provider.__class__.__name__}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
