"""Cost governance — tracks token spend and enforces per-run budget limits."""
from __future__ import annotations
import json
import os
from decimal import Decimal
from db.session import db

# Cost per 1M tokens (USD) — defaults, overridable via env
COST_PER_1M = {
    "input":  float(os.getenv("COST_PER_1M_INPUT",  "3.0")),
    "output": float(os.getenv("COST_PER_1M_OUTPUT", "15.0")),
}
MAX_COST_PER_RUN = float(os.getenv("MAX_COST_PER_RUN_USD", "0.50"))
MAX_TOKENS_PER_RUN = int(os.getenv("MAX_TOKENS_PER_RUN", "200000"))


class CostGovernanceService:

    def record(self, review_run_id: str, agent_id: str, input_tokens: int, output_tokens: int,
               cached_tokens: int, provider: str, model: str) -> None:
        cost = (input_tokens * COST_PER_1M["input"] + output_tokens * COST_PER_1M["output"]) / 1_000_000
        prompt_hash = ""
        with db() as conn:
            conn.execute(
                """INSERT INTO llm_requests
                   (review_run_id, agent_id, provider, model, prompt_hash,
                    input_tokens, output_tokens, cached_tokens, cost_usd, status)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (review_run_id, agent_id, provider, model, prompt_hash,
                 input_tokens, output_tokens, cached_tokens, cost, "completed"),
            )

    def check_budget(self, review_run_id: str) -> tuple[bool, str]:
        """Returns (ok, reason). Call before each LLM call."""
        with db() as conn:
            row = conn.execute(
                """SELECT COALESCE(SUM(input_tokens+output_tokens),0) AS total_tokens,
                          COALESCE(SUM(cost_usd),0) AS total_cost
                   FROM llm_requests WHERE review_run_id=?""",
                (review_run_id,),
            ).fetchone()

        if int(row["total_tokens"]) >= MAX_TOKENS_PER_RUN:
            return False, f"Token budget exceeded: {row['total_tokens']} >= {MAX_TOKENS_PER_RUN}"
        if float(row["total_cost"]) >= MAX_COST_PER_RUN:
            return False, f"Cost budget exceeded: ${float(row['total_cost']):.4f} >= ${MAX_COST_PER_RUN}"
        return True, ""

    def summary(self, review_run_id: str) -> dict:
        with db() as conn:
            row = conn.execute(
                """SELECT COALESCE(SUM(input_tokens),0) AS input_tokens,
                          COALESCE(SUM(output_tokens),0) AS output_tokens,
                          COALESCE(SUM(cached_tokens),0) AS cached_tokens,
                          COALESCE(SUM(cost_usd),0) AS cost_usd
                   FROM llm_requests WHERE review_run_id=?""",
                (review_run_id,),
            ).fetchone()
        d = dict(row)
        return {k: float(v) if isinstance(v, Decimal) else v for k, v in d.items()}
