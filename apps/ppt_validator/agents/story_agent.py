"""Story agent — evaluates narrative arc and logical flow across the full deck."""
from __future__ import annotations
import json
from agents.base import AgentContract, ReviewAgent
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent


class StoryAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "story"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]
            prompt = self._get_prompt(context)
            user = self._format_prompt(prompt["user_template"],
                slides=json.dumps(ppt.slim_slides("bullets"), ensure_ascii=False),
                slide_count=ppt.slide_count,
            )
            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))
            if raw is None:
                return AgentContract(agent_id=self.agent_id, status="budget_exceeded", score=0)

            findings = self._parse_findings(raw)
            # Enforce: slide 1 is always a title/cover slide — strip any opening hook findings on it
            findings = [f for f in findings if f.slide != 1]

            # Compute estimated presentation duration (approx 1.5 mins per slide, or 130 words per minute)
            total_words = sum(s.word_count for s in ppt.slides)
            est_mins_by_words = max(1, round(total_words / 130.0))
            est_mins_by_slides = max(1, round(ppt.slide_count * 1.75))
            estimated_minutes = max(est_mins_by_words, est_mins_by_slides)

            # Determine delivery format suitability
            avg_words_per_slide = (total_words / ppt.slide_count) if ppt.slide_count > 0 else 0
            delivery_format = "Email Leave-Behind" if avg_words_per_slide > 70 else "In-Person Presentation"

            summary = raw.get("summary", "")
            if "minutes" not in summary.lower():
                summary = f"{summary.strip()} | Format: {delivery_format} | Est. Duration: ~{estimated_minutes} mins."

            return AgentContract(
                agent_id=self.agent_id, status="completed",
                score=int(raw.get("score", 70)),
                findings=findings, summary=summary,
                metadata={
                    "estimated_minutes": estimated_minutes,
                    "delivery_format": delivery_format,
                    "total_words": total_words,
                }
            )
        except Exception as exc:
            return self._failed(str(exc))


register_agent("story", StoryAgent, stage="content_extraction", execution_mode="parallel")
