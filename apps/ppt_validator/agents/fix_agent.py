"""Fix Agent — generates actionable step-by-step fix recommendations for slide authors."""
from __future__ import annotations
import json
from agents.base import AgentContract, ReviewAgent, AgentStatus, ActionType
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent


class FixAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "fix_agent"

    def run(self, context: dict) -> AgentContract:
        try:
            findings = context.get("findings", [])
            if not findings:
                return AgentContract(
                    agent_id=self.agent_id,
                    status=AgentStatus.PASS,
                    score=100,
                    summary="No review findings to generate fix recommendations for.",
                )

            prompt = self._get_prompt(context)
            findings_json = json.dumps([
                {
                    "id": getattr(f, "id", f"FND-{i+1:03d}"),
                    "slide": f.slide,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                }
                for i, f in enumerate(findings)
            ], ensure_ascii=False)

            user = self._format_prompt(
                prompt["user_template"],
                filename=context.get("original_filename", "presentation.pptx"),
                findings=findings_json,
            )

            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))
            if raw is None:
                return AgentContract(agent_id=self.agent_id, status=AgentStatus.BUDGET_EXCEEDED, score=0)

            recommendations = []
            if isinstance(raw, dict):
                recs_list = raw.get("recommendations", [])
                for r in recs_list:
                    recommendations.append({
                        "slide": r.get("slide", 0),
                        "finding_id": r.get("finding_id", ""),
                        "issue_title": r.get("issue_title", ""),
                        "fix_recommendation": r.get("fix_recommendation", r.get("recommendation", "")),
                        "action_type": ActionType.RECOMMENDATION_ONLY.value,
                    })

            summary = (
                raw.get("summary")
                if isinstance(raw, dict) and raw.get("summary")
                else f"Generated {len(recommendations)} actionable fix recommendations for author review."
            )

            return AgentContract(
                agent_id=self.agent_id,
                status=AgentStatus.PASS,
                score=100,
                summary=summary,
                metadata={"recommendations": recommendations},
            )
        except Exception as exc:
            return self._failed(str(exc))


register_agent("fix_agent", FixAgent, stage="fix", execution_mode="sequential", enabled_by_default=False)
