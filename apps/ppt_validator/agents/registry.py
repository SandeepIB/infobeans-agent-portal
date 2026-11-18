"""Agent registry — holds AGENT_REGISTRY dict and register_agent() helper.

Separate from review_service to avoid circular imports:
  review_service → agents.base → agents/__init__ → agents/* → (was) review_service
  Now: agents/* → agents.registry  (no cycle)
"""
from __future__ import annotations

AGENT_REGISTRY: dict[str, dict] = {}

STAGES = ["extraction", "content_extraction", "cross_slide", "aggregation"]


def register_agent(
    agent_id: str,
    cls: type,
    stage: str,
    execution_mode: str = "parallel",
    enabled_by_default: bool = True,
    cacheability: str = "slide_level",
) -> None:
    AGENT_REGISTRY[agent_id] = {
        "cls": cls,
        "stage": stage,
        "execution_mode": execution_mode,
        "enabled_by_default": enabled_by_default,
        "cacheability": cacheability,
    }
