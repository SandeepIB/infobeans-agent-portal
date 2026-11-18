"""Agents API — list registered agents and registry metadata."""
from fastapi import APIRouter
import agents  # noqa: F401
from services.review_service import AGENT_REGISTRY

router = APIRouter(prefix="/api/v2/agents", tags=["agents"])


@router.get("")
def list_agents():
    return [
        {
            "agent_id": aid,
            "stage": meta["stage"],
            "execution_mode": meta["execution_mode"],
            "enabled_by_default": meta["enabled_by_default"],
            "cacheability": meta["cacheability"],
        }
        for aid, meta in AGENT_REGISTRY.items()
    ]
