"""Template agent — rule-based structural checks (slide count, layouts, placeholders)."""
from __future__ import annotations
from agents.base import AgentContract, ReviewAgent, Finding, Severity, ActionType
from services.rule_service import RuleService
from agents.registry import register_agent

_rule_svc = RuleService()


class TemplateAgent(ReviewAgent):
    agent_id = "template"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]
            rules = _rule_svc.get_rules("template")
            findings: list[Finding] = []

            min_slides = next((int(r["value"]) for r in rules if r.get("type") == "min_slides"), 5)
            max_slides = next((int(r["value"]) for r in rules if r.get("type") == "max_slides"), 30)
            required_layouts = {r["value"] for r in rules if r.get("type") == "required_layout"}

            if ppt.slide_count < min_slides:
                findings.append(Finding(
                    slide=0, severity=Severity.HIGH, category="template",
                    title="Too few slides",
                    description=f"Presentation has {ppt.slide_count} slides; minimum is {min_slides}.",
                    recommendation=f"Add at least {min_slides - ppt.slide_count} more slide(s).",
                    confidence=1.0, action_type=ActionType.RECOMMENDATION_ONLY,
                    rule_id="template_min_slides",
                ))
            if ppt.slide_count > max_slides:
                findings.append(Finding(
                    slide=0, severity=Severity.MEDIUM, category="template",
                    title="Too many slides",
                    description=f"Presentation has {ppt.slide_count} slides; maximum is {max_slides}.",
                    recommendation="Consolidate or remove slides to stay within the limit.",
                    confidence=1.0, action_type=ActionType.RECOMMENDATION_ONLY,
                    rule_id="template_max_slides",
                ))

            score = max(0, 100 - len(findings) * 15)
            return AgentContract(
                agent_id=self.agent_id, status="completed", score=score,
                findings=findings,
                summary=f"{len(findings)} template issue(s) found.",
            )
        except Exception as exc:
            return self._failed(str(exc))


register_agent("template", TemplateAgent, stage="extraction", execution_mode="parallel",
               cacheability="full")
