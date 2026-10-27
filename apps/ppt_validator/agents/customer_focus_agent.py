"""Customer focus agent — evaluates customer-centricity and audience alignment."""
from __future__ import annotations
import json
from agents.base import AgentContract, ReviewAgent
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent


class CustomerFocusAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "customer_focus"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]
            profile = context.get("profile", {})
            prompt = self._get_prompt(context)
            user = self._format_prompt(prompt["user_template"],
                slides=json.dumps(ppt.slim_slides("bullets"), ensure_ascii=False),
                customer=profile.get("customer", "Unknown"),
                audience=profile.get("audience", "Unknown"),
                objective=profile.get("objective", ""),
                industry=profile.get("industry", ""),
            )
            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))
            if raw is None:
                return AgentContract(agent_id=self.agent_id, status="budget_exceeded", score=0)

            findings = self._parse_findings(raw)
            # Enforce: slide 1 is always a cover slide — strip any WIIFM findings on it
            findings = [f for f in findings if f.slide != 1]

            return AgentContract(
                agent_id=self.agent_id, status="completed",
                score=int(raw.get("score", 70)),
                findings=findings,
                summary=raw.get("summary", ""),
            )
        except Exception as exc:
            return self._failed(str(exc))


register_agent("customer_focus", CustomerFocusAgent, stage="content_extraction", execution_mode="parallel")
