"""Review orchestrator — builds execution plan from registry + profile, runs DAG."""
from __future__ import annotations
import concurrent.futures
import json
import os
import uuid
from decimal import Decimal
from datetime import datetime, timezone


def _mysql_dt(dt: datetime) -> str:
    """Format a datetime as 'YYYY-MM-DD HH:MM:SS' for MySQL DATETIME columns.

    MySQL rejects ISO 8601 strings that contain a 'T' separator, microseconds,
    or a timezone offset such as '+00:00'.
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")
from pathlib import Path

import structlog

from agents.base import AgentContract, ReviewAgent  # noqa: F401
from agents.registry import AGENT_REGISTRY, STAGES
from db.session import db
from services.cost_governance_service import CostGovernanceService
from services.ppt_service import PPTService, PPTData
from services.slide_match_service import SlideMatchService, DEFAULT_EXCLUDE_TEMPLATE_PATH

logger = structlog.get_logger()


class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _dumps(obj) -> str:
    return json.dumps(obj, cls=_DecimalEncoder)


# Re-export so existing callers work without change
from agents.registry import register_agent  # noqa: E402, F401


import contextvars

try:
    from langsmith import traceable
    from langsmith.run_helpers import get_current_run_tree
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def get_current_run_tree():
        return None


from services.normalization_service import NormalizationService

DEFAULT_DIMENSION_WEIGHTS = {
    "branding": 0.10,
    "template": 0.10,
    "visual_quality": 0.10,
    "content": 0.20,
    "story": 0.15,
    "customer_focus": 0.15,
    "proposal_context": 0.10,
    "cio_lens": 0.10,
}


class ReviewService:
    def __init__(self):
        self.ppt_service = PPTService()
        self.cost = CostGovernanceService()
        self.slide_match_service = SlideMatchService(self.ppt_service)
        self.normalizer = NormalizationService()

    def run(self, file_path: str, profile: dict, proposal_context: str | None = None,
            original_filename: str | None = None) -> dict:
        run_id = str(uuid.uuid4())
        display_name = original_filename or Path(file_path).name
        project_name = os.getenv("LANGSMITH_PROJECT", "infobeans-infobeans_ppt_validate")

        if LANGSMITH_AVAILABLE:
            @traceable(name=f"ppt_review ({display_name})", run_type="chain", tags=[run_id, display_name])
            def _traced_run():
                return self._do_run(run_id, file_path, profile, proposal_context, display_name)
            return _traced_run()
        else:
            return self._do_run(run_id, file_path, profile, proposal_context, display_name)

    def _do_run(self, run_id: str, file_path: str, profile: dict, proposal_context: str | None,
                display_name: str) -> dict:
        started_at = _mysql_dt(datetime.now(timezone.utc))
        self._persist_run(run_id, file_path, profile, started_at, display_name)

        try:
            ppt_data = self.ppt_service.extract(file_path)
            template_path = profile.get("exclude_template_path") or os.getenv("EXCLUDE_TEMPLATE_PATH", DEFAULT_EXCLUDE_TEMPLATE_PATH)
            exclusions = self.slide_match_service.find_matched_slides(ppt_data, template_path=template_path)
            excluded_slide_numbers = [e["slide_number"] for e in exclusions]
            if exclusions:
                logger.info("slides_excluded_from_review", run_id=run_id, count=len(exclusions), excluded_slides=excluded_slide_numbers, details=[e["detail"] for e in exclusions])
            self._persist_exclusions(run_id, exclusions)

            context = self._build_context(run_id, ppt_data, profile, proposal_context,
                                          excluded_slides=excluded_slide_numbers, slide_exclusions=exclusions)
            agent_results = self._execute_dag(run_id, context, profile)

            # Collect raw findings across all agents & normalize/deduplicate
            all_raw_findings = [f for r in agent_results for f in r.findings]
            normalized_findings = self.normalizer.normalize_and_deduplicate(all_raw_findings)

            score, quality_gate, dimension_scores = self._aggregate(agent_results, profile)
            cost_summary = self.cost.summary(run_id)
            total_input = int(cost_summary.get("input_tokens", 0))
            total_output = int(cost_summary.get("output_tokens", 0))
            total_tokens = total_input + total_output

            # Executive Report Formatting
            critical_issues = [self._finding_to_dict(f) for f in normalized_findings if str(f.severity) == "HIGH"]
            important_improvements = [self._finding_to_dict(f) for f in normalized_findings if str(f.severity) == "MEDIUM"]
            strengths = [r.summary for r in agent_results if r.score >= 85 and r.summary]
            top_recommendations = [f.recommendation for f in normalized_findings if f.recommendation][:5]

            result = {
                "run_id": run_id,
                "filename": display_name,
                "status": "completed",
                "quality_gate": quality_gate,
                "score": score,
                "dimension_scores": dimension_scores,
                "total_llm_calls": len([r for r in agent_results if r.agent_id in ("story", "content", "customer_focus", "proposal_context", "cio_lens", "critic", "visual_quality", "evidence_claims")]),
                "usage_metadata": {
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "total_tokens": total_tokens,
                },
                "agent_results": [self._contract_to_dict(r) for r in agent_results],
                "normalized_findings": [self._finding_to_dict(f) for f in normalized_findings],
                "executive_summary": {
                    "overall_score": score,
                    "dimension_scores": dimension_scores,
                    "critical_issues": critical_issues,
                    "important_improvements": important_improvements,
                    "strengths": strengths,
                    "top_recommendations": top_recommendations,
                },
                "excluded_slides": exclusions,
                "cost": cost_summary,
                "started_at": started_at,
                "completed_at": _mysql_dt(datetime.now(timezone.utc)),
            }
            self._update_run(run_id, score, "completed", result)
            return result
        except Exception as exc:
            logger.error("review_failed", run_id=run_id, error=str(exc))
            self._update_run(run_id, 0, "failed", {"error": str(exc)})
            raise

    def _build_context(self, run_id: str, ppt_data: PPTData, profile: dict,
                       proposal_context: str | None,
                       excluded_slides: list[int] | None = None,
                       slide_exclusions: list[dict] | None = None) -> dict:
        parent_tree = get_current_run_tree() if LANGSMITH_AVAILABLE else None
        return {
            "run_id": run_id,
            "ppt_data": ppt_data,
            "profile": profile,
            "proposal_context": proposal_context,
            "excluded_slides": excluded_slides or [],
            "slide_exclusions": slide_exclusions or [],
            "parent_run_tree": parent_tree,
        }

    def _execute_dag(self, run_id: str, context: dict, profile: dict) -> list[AgentContract]:
        enabled = self._enabled_agents(profile)
        all_results: list[AgentContract] = []

        for stage in STAGES:
            stage_agents = [
                (aid, meta) for aid, meta in AGENT_REGISTRY.items()
                if meta["stage"] == stage and aid in enabled
            ]
            if not stage_agents:
                continue

            parallel = [(aid, m) for aid, m in stage_agents if m["execution_mode"] == "parallel"]
            sequential = [(aid, m) for aid, m in stage_agents if m["execution_mode"] == "sequential"]

            if parallel:
                all_results.extend(self._run_parallel(run_id, parallel, context))
            for aid, meta in sequential:
                all_results.append(self._run_agent(run_id, aid, meta, context))

        return all_results

    def _run_parallel(self, run_id: str, agents: list, context: dict) -> list[AgentContract]:
        max_workers = int(os.getenv("MAX_PARALLEL_AGENTS", "4"))
        results = []

        def _worker(aid, meta):
            return contextvars.copy_context().run(self._run_agent, run_id, aid, meta, context)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_worker, aid, meta): aid for aid, meta in agents}
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())
        return results

    def _run_agent(self, run_id: str, agent_id: str, meta: dict, context: dict) -> AgentContract:
        ok, reason = self.cost.check_budget(run_id)
        if not ok:
            return AgentContract(agent_id=agent_id, status="budget_exceeded", score=0, summary=reason)

        agent: ReviewAgent = meta["cls"]()
        try:
            result = agent.run({**context, "agent_id": agent_id})
        except Exception as exc:
            logger.error("agent_error", agent_id=agent_id, error=str(exc))
            result = AgentContract(agent_id=agent_id, status="failed", score=0, summary=str(exc))

        self._persist_agent_run(run_id, result)
        return result

    def _enabled_agents(self, profile: dict) -> set[str]:
        profile_agents = {a["id"]: a["enabled"] for a in profile.get("agents", [])}
        enabled = set()
        for aid, meta in AGENT_REGISTRY.items():
            if aid in profile_agents:
                if profile_agents[aid]:
                    enabled.add(aid)
            elif meta["enabled_by_default"]:
                enabled.add(aid)
        return enabled

    def _aggregate(self, results: list[AgentContract], profile: dict) -> tuple[int, str, dict[str, int]]:
        if not results:
            return 0, "failed", {}

        valid_results = [r for r in results if r.status in ("completed", "PASS", "FAIL", "PARTIAL")]
        if not valid_results:
            return 0, "failed", {}

        # Profile custom weights or default weights
        custom_weights = profile.get("weights", {})
        weights = {**DEFAULT_DIMENSION_WEIGHTS, **custom_weights}

        dimension_scores: dict[str, int] = {}
        total_weight = 0.0
        weighted_score_sum = 0.0

        for r in valid_results:
            dimension_scores[r.agent_id] = r.score
            w = weights.get(r.agent_id, 0.0)
            if w > 0:
                weighted_score_sum += r.score * w
                total_weight += w

        if total_weight > 0:
            final_score = round(weighted_score_sum / total_weight)
        else:
            final_score = round(sum(r.score for r in valid_results) / len(valid_results))

        if final_score >= 80:
            quality_gate = "ready"
        elif final_score >= 60:
            quality_gate = "review"
        else:
            quality_gate = "blocked"

        return final_score, quality_gate, dimension_scores

    def _finding_to_dict(self, f) -> dict:
        return {
            "id": getattr(f, "id", None),
            "slide": f.slide,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "category": f.category,
            "title": f.title,
            "description": f.description,
            "finding": f.description,
            "evidence": f.evidence_text if hasattr(f, "evidence_text") else str(getattr(f, "evidence", "")),
            "recommendation": f.recommendation,
            "confidence": f.confidence,
            "action_type": f.action_type.value if hasattr(f.action_type, "value") else str(f.action_type),
            "rule_id": getattr(f, "rule_id", None),
        }

    def _contract_to_dict(self, c: AgentContract) -> dict:
        status_val = c.status.value if hasattr(c.status, "value") else str(c.status)
        return {
            "agent_id": c.agent_id,
            "status": status_val,
            "score": c.score,
            "summary": c.summary,
            "confidence": c.confidence,
            "findings": [self._finding_to_dict(f) for f in c.findings],
            "metadata": c.metadata,
        }

    def _persist_run(self, run_id: str, file_path: str, profile: dict, started_at: str,
                     original_filename: str | None = None) -> None:
        display_name = original_filename or Path(file_path).name
        with db() as conn:
            conn.execute(
                """INSERT INTO review_runs
                   (id, run_id, filename, ppt_filename, ppt_hash, review_profile, profile_json, status, started_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (run_id, run_id, display_name, display_name, "",
                 _dumps(profile), _dumps(profile), "running", started_at),
            )

    def _update_run(self, run_id: str, score: int, status: str, result: dict) -> None:
        with db() as conn:
            conn.execute(
                "UPDATE review_runs SET score=?, status=?, result_json=?, completed_at=? WHERE id=?",
                (score, status, _dumps(result), _mysql_dt(datetime.now(timezone.utc)), run_id),
            )

    def _persist_agent_run(self, run_id: str, result: AgentContract) -> None:
        with db() as conn:
            conn.execute(
                """INSERT INTO agent_runs (review_run_id, agent_id, status, score, findings_json, summary)
                   VALUES (?,?,?,?,?,?)""",
                (run_id, result.agent_id, result.status, result.score,
                 _dumps(self._contract_to_dict(result)["findings"]), result.summary),
            )

    def _persist_exclusions(self, run_id: str, exclusions: list[dict]) -> None:
        if not exclusions:
            return
        with db() as conn:
            for exc in exclusions:
                conn.execute(
                    """INSERT INTO slide_exclusions
                       (review_run_id, slide_number, excluded_agents, reason, detail, reference_template_id)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        run_id,
                        exc["slide_number"],
                        _dumps(exc["excluded_agents"]),
                        exc["reason"],
                        exc["detail"],
                        exc["reference_template_id"],
                    ),
                )
            conn.execute(
                "UPDATE review_runs SET exclude_slides=? WHERE id=?",
                (_dumps([e["slide_number"] for e in exclusions]), run_id),
            )

