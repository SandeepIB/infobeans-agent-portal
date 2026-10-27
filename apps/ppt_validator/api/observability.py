"""Observability API — cost summaries and LLM request logs."""
from fastapi import APIRouter, HTTPException
from services.cost_governance_service import CostGovernanceService
from db.session import db

router = APIRouter(prefix="/api/v2/observability", tags=["observability"])
_cost = CostGovernanceService()


@router.get("/cost/{run_id}")
def cost_summary(run_id: str):
    return _cost.summary(run_id)


@router.get("/requests/{run_id}")
def llm_requests(run_id: str):
    with db() as conn:
        rows = conn.execute(
            """SELECT agent_id, provider, model, input_tokens, output_tokens,
                      cached_tokens, cost_usd, created_at
               FROM llm_requests WHERE review_run_id=? ORDER BY created_at""",
            (run_id,),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No requests found for this run")
    return [dict(r) for r in rows]
