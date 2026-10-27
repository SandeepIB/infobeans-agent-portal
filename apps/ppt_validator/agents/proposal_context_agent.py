"""Proposal context agent — checks PPT coverage against proposal requirements."""
from __future__ import annotations
import json
from agents.base import AgentContract, ReviewAgent, Finding, Severity, ActionType
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent


DIMENSIONS = [
    "problem_statement", "proposed_solution", "technical_approach",
    "timeline_milestones", "team_credentials", "pricing_commercials",
    "risk_mitigation", "success_metrics",
]


class ProposalContextAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "proposal_context"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]
            proposal_context = context.get("proposal_context", "")
            if not proposal_context:
                return AgentContract(
                    agent_id=self.agent_id, status="skipped", score=100,
                    summary="No proposal context provided — skipped.",
                )

            prompt = self._get_prompt(context)
            slides_text = ppt.slim_slides("full_text")  # proposal check needs full text
            user = self._format_prompt(prompt["user_template"],
                slides=json.dumps(slides_text, ensure_ascii=False),
                proposal_context=proposal_context[:3000],
                dimensions=json.dumps(DIMENSIONS),
            )
            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))
            if raw is None:
                return AgentContract(agent_id=self.agent_id, status="budget_exceeded", score=0)

            findings = self._parse_findings(raw)
            # Add missing dimension findings
            for dim in raw.get("missing_dimensions", []):
                findings.append(Finding(
                    slide=0, severity=Severity.HIGH, category="proposal_coverage",
                    title=f"Missing: {dim}",
                    description=f"Proposal dimension '{dim}' not addressed in the presentation.",
                    recommendation=f"Add a slide covering {dim}.",
                    confidence=0.85, action_type=ActionType.RECOMMENDATION_ONLY,
                ))

            return AgentContract(
                agent_id=self.agent_id, status="completed",
                score=int(raw.get("score", 70)),
                findings=findings, summary=raw.get("summary", ""),
            )
        except Exception as exc:
            return self._failed(str(exc))


register_agent("proposal_context", ProposalContextAgent, stage="content_extraction",
               execution_mode="parallel", enabled_by_default=False)
