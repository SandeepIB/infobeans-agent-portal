"""Content agent — evaluates content quality, clarity, and deck-wide consistency (date format, currency, terminology)."""
from __future__ import annotations
import json
import re
from agents.base import AgentContract, ReviewAgent, Finding, Severity, ActionType
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent
from services.normalization_service import NormalizationService


class ContentAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "content"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]

            # 1. Execute deterministic deck-wide consistency rule checks
            rule_findings = self._run_consistency_checks(ppt)

            # 2. Execute qualitative LLM content & consistency review
            prompt = self._get_prompt(context)
            user = self._format_prompt(
                prompt["user_template"],
                slides=json.dumps(ppt.slim_slides("bullets"), ensure_ascii=False),
                slide_count=ppt.slide_count,
            )
            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))

            llm_findings = []
            if raw and isinstance(raw, dict):
                llm_findings = self._parse_findings(raw)

            # 3. Combine and deduplicate findings
            all_findings = rule_findings + llm_findings
            normalizer = NormalizationService(similarity_threshold=0.25)
            consolidated_findings = normalizer.normalize_and_deduplicate(all_findings)

            # 4. Score calculation
            base_score = int(raw.get("score", 85)) if (raw and isinstance(raw, dict)) else 80
            rule_penalty = len(rule_findings) * 5
            final_score = max(0, min(100, base_score - rule_penalty))

            summary = (
                raw.get("summary")
                if (raw and isinstance(raw, dict) and raw.get("summary"))
                else f"Content quality review completed with {len(consolidated_findings)} findings."
            )

            return AgentContract(
                agent_id=self.agent_id,
                status="completed",
                score=final_score,
                findings=consolidated_findings,
                summary=summary,
                metadata={"prompt_version_id": prompt.get("version_id")},
            )
        except Exception as exc:
            return self._failed(str(exc))

    def _run_consistency_checks(self, ppt) -> list[Finding]:
        findings: list[Finding] = []

        slide_date_styles: dict[int, set[str]] = {}
        slide_currencies: dict[int, set[str]] = {}

        # Patterns
        iso_date_pat = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')
        us_date_pat = re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b')
        named_date_pat = re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', re.IGNORECASE)
        quarter_date_pat = re.compile(r'\bQ[1-4]\s?\d{2,4}\b', re.IGNORECASE)

        usd_sym_pat = re.compile(r'\$\d+')
        usd_str_pat = re.compile(r'\bUSD\b', re.IGNORECASE)
        eur_pat = re.compile(r'€|\bEUR\b', re.IGNORECASE)
        gbp_pat = re.compile(r'£|\bGBP\b', re.IGNORECASE)

        for slide in ppt.slides:
            full_text = f"{slide.title} {slide.body_text} {' '.join(slide.bullets)}"

            # Dates
            styles = set()
            if iso_date_pat.search(full_text):
                styles.add("YYYY-MM-DD")
            if us_date_pat.search(full_text):
                styles.add("MM/DD/YYYY")
            if named_date_pat.search(full_text):
                styles.add("Month DD, YYYY")
            if quarter_date_pat.search(full_text):
                styles.add("Quarterly (Q1-Q4)")
            if styles:
                slide_date_styles[slide.number] = styles

            # Currencies
            currs = set()
            if usd_sym_pat.search(full_text):
                currs.add("$ Symbol ($10M)")
            if usd_str_pat.search(full_text):
                currs.add("USD Text (10M USD)")
            if eur_pat.search(full_text):
                currs.add("EUR / €")
            if gbp_pat.search(full_text):
                currs.add("GBP / £")
            if currs:
                slide_currencies[slide.number] = currs

        # Analyze Date Format Consistency across deck
        all_date_styles: set[str] = set()
        for styles in slide_date_styles.values():
            all_date_styles.update(styles)
        if len(all_date_styles) > 1:
            affected_slides = ", ".join(f"Slide {s}" for s in sorted(slide_date_styles.keys()))
            styles_str = ", ".join(sorted(all_date_styles))
            findings.append(Finding(
                id="CNT-CONSIST-001",
                slide=0,
                severity=Severity.MEDIUM,
                category="consistency",
                title="Inconsistent date formatting across slides",
                description=f"Presentation uses mixed date formats ({styles_str}) across slides ({affected_slides}).",
                recommendation="Standardize all date representations throughout the presentation to a single uniform date format (e.g. Month DD, YYYY).",
                confidence=0.95,
                action_type=ActionType.RECOMMENDATION_ONLY,
                evidence=f"Multiple date formats detected across deck: {styles_str}.",
                rule_id="CNT-CONSIST-001",
            ))

        # Analyze Currency Formatting Consistency across deck
        all_currencies: set[str] = set()
        for currs in slide_currencies.values():
            all_currencies.update(currs)
        if len(all_currencies) > 1 and ("$ Symbol ($10M)" in all_currencies and "USD Text (10M USD)" in all_currencies):
            affected_slides = ", ".join(f"Slide {s}" for s in sorted(slide_currencies.keys()))
            findings.append(Finding(
                id="CNT-CONSIST-002",
                slide=0,
                severity=Severity.MEDIUM,
                category="consistency",
                title="Inconsistent currency formatting ($ vs USD)",
                description=f"Presentation mixes currency formats ('$' symbol vs 'USD' code) across slides ({affected_slides}).",
                recommendation="Standardize currency references to a single format across all slides (e.g. use '$' or 'USD' consistently).",
                confidence=0.95,
                action_type=ActionType.RECOMMENDATION_ONLY,
                evidence="Mixed use of '$' symbol and 'USD' text code detected across slides.",
                rule_id="CNT-CONSIST-002",
            ))

        return findings


register_agent("content", ContentAgent, stage="content_extraction", execution_mode="parallel")
