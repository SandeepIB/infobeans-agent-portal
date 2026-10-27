"""Critic agent — meta-reviewer that challenges findings for false positives/negatives."""
from __future__ import annotations
import json
from agents.base import AgentContract, ReviewAgent
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent


class CriticAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "critic"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]
            prompt = self._get_prompt(context)
            # Critic only needs titles + word count — titles_only tier
            deck_overview = {
                "slide_count": ppt.slide_count,
                "total_words": sum(s.word_count for s in ppt.slides),
                "slides": ppt.slim_slides("titles_only"),
            }
            user = self._format_prompt(prompt["user_template"],
                deck=json.dumps(deck_overview, ensure_ascii=False),
            )
            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))
            if raw is None:
                return AgentContract(agent_id=self.agent_id, status="budget_exceeded", score=0)

            return AgentContract(
                agent_id=self.agent_id, status="completed",
                score=int(raw.get("score", 80)),
                findings=self._parse_findings(raw),
                summary=raw.get("summary", ""),
                metadata={"cacheability": "none"},
            )
        except Exception as exc:
            return self._failed(str(exc))


register_agent("critic", CriticAgent, stage="cross_slide", execution_mode="sequential",
               cacheability="none")
