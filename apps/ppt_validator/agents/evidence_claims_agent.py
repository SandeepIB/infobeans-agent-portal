"""Evidence and claims agent — audits technical/business claims, metric consistency, and proof."""
from __future__ import annotations
import json
from agents.base import AgentContract, ReviewAgent, AgentStatus
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent


class EvidenceClaimsAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "evidence_claims"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]
            proposal_context = context.get("proposal_context") or "No proposal context provided."
            prompt = self._get_prompt(context)
            user = self._format_prompt(
                prompt["user_template"],
                slides=json.dumps(ppt.slim_slides("full_text"), ensure_ascii=False),
                slide_count=ppt.slide_count,
                proposal_context=proposal_context[:3000],
            )
            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))
            if raw is None:
                return AgentContract(agent_id=self.agent_id, status=AgentStatus.BUDGET_EXCEEDED, score=0)

            findings = self._parse_findings(raw)
            status_str = raw.get("status", "PASS") if isinstance(raw, dict) else "PASS"
            status = AgentStatus(status_str) if status_str in AgentStatus._value2member_map_ else AgentStatus.PASS

            return AgentContract(
                agent_id=self.agent_id,
                status=status,
                score=int(raw.get("score", 85)),
                findings=findings,
                summary=raw.get("summary", ""),
                confidence=float(raw.get("confidence", 0.90)),
            )
        except Exception as exc:
            return self._failed(str(exc))


register_agent("evidence_claims", EvidenceClaimsAgent, stage="content_extraction", execution_mode="parallel")
