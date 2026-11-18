"""CIO Lens agent — cross-slide executive readiness and strategic alignment."""
from __future__ import annotations
import json
from agents.base import AgentContract, ReviewAgent
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent


class CIOLensAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "cio_lens"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]
            profile = context.get("profile", {})
            prompt = self._get_prompt(context)
            # CIO lens is cross-slide — titles_only is enough for structure check;
            # key_content uses bullets tier for substance
            deck_summary = {
                "slide_count": ppt.slide_count,
                "slides": ppt.slim_slides("bullets"),
            }
            user = self._format_prompt(prompt["user_template"],
                deck=json.dumps(deck_summary, ensure_ascii=False),
                audience=profile.get("audience", "Executive"),
                presentation_level=profile.get("presentation_level", "executive"),
                objective=profile.get("objective", ""),
            )
            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))
            if raw is None:
                return AgentContract(agent_id=self.agent_id, status="budget_exceeded", score=0)

            return AgentContract(
                agent_id=self.agent_id, status="completed",
                score=int(raw.get("score", 70)),
                findings=self._parse_findings(raw),
                summary=raw.get("summary", ""),
            )
        except Exception as exc:
            return self._failed(str(exc))


register_agent("cio_lens", CIOLensAgent, stage="cross_slide", execution_mode="sequential")
