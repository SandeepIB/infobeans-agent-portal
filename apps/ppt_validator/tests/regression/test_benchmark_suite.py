"""Regression Benchmark Suite — validates JSON validity, enum safety, evidence presence, deduplication, scoring, and fix_agent safety."""
from __future__ import annotations
import json
import pytest
from agents.base import (
    Finding, Severity, ActionType, AgentContract, AgentStatus
)
from agents.llm_mixin import LLMAgentMixin
from agents.visual_quality_agent import VisualQualityAgent
from agents.content_agent import ContentAgent
from agents.fix_agent import FixAgent
from services.normalization_service import NormalizationService
from services.review_service import ReviewService


class DummyLLMAgent(LLMAgentMixin):
    agent_id = "test_agent"


def test_enum_standardization():
    """Verify that Severity and ActionType enums conform strictly to specification."""
    assert Severity.HIGH.value == "HIGH"
    assert Severity.MEDIUM.value == "MEDIUM"
    assert Severity.LOW.value == "LOW"
    assert Severity.INFO.value == "INFO"

    assert ActionType.AUTO_FIXABLE.value == "AUTO_FIXABLE"
    assert ActionType.HUMAN_REVIEW_REQUIRED.value == "HUMAN_REVIEW_REQUIRED"
    assert ActionType.RECOMMENDATION_ONLY.value == "RECOMMENDATION_ONLY"


def test_finding_parsing_and_evidence_extraction():
    """Verify that LLMAgentMixin parses raw LLM JSON with evidence and confidence validation."""
    agent = DummyLLMAgent()
    raw = {
        "score": 82,
        "summary": "Sample review",
        "findings": [
            {
                "slide": 3,
                "severity": "CRITICAL",  # Should map to HIGH
                "action_type": "AUTO_FIX",  # Should map to AUTO_FIXABLE
                "finding": "Slide has visual clutter.",
                "evidence": "Slide 3 contains 12 bullets and overlapping text boxes.",
                "recommendation": "Reduce bullets to 5.",
                "confidence": 0.95
            },
            {
                "slide": 5,
                "severity": "MEDIUM",
                "action_type": "HUMAN_APPROVAL",  # Should map to HUMAN_REVIEW_REQUIRED
                "finding": "Unclear ROI statement.",
                "evidence": "Slide 5 states cost savings without baseline.",
                "recommendation": "Add cost baseline metric.",
                "confidence": 1.5  # Clamped to 1.0
            }
        ]
    }
    findings = agent._parse_findings(raw)
    assert len(findings) == 2

    # Finding 1 assertions
    f1 = findings[0]
    assert f1.slide == 3
    assert f1.severity == Severity.HIGH
    assert f1.action_type == ActionType.AUTO_FIXABLE
    assert f1.evidence_text == "Slide 3 contains 12 bullets and overlapping text boxes."
    assert f1.confidence == 0.95

    # Finding 2 assertions
    f2 = findings[1]
    assert f2.severity == Severity.MEDIUM
    assert f2.action_type == ActionType.HUMAN_REVIEW_REQUIRED
    assert f2.confidence == 1.0


def test_cross_agent_deduplication_and_normalization():
    """Verify that NormalizationService merges duplicate findings across agents."""
    normalizer = NormalizationService()

    f_content = Finding(
        id="CNT-001",
        slide=4,
        severity=Severity.MEDIUM,
        category="content",
        title="Excessive technical jargon",
        description="Slide 4 contains excessive technical jargon obscuring business impact.",
        recommendation="Simplify technical language.",
        confidence=0.85,
        action_type=ActionType.RECOMMENDATION_ONLY,
        evidence="Slide 4 lists 15 Kubernetes and Kafka parameters.",
    )

    f_cio = Finding(
        id="CIO-001",
        slide=4,
        severity=Severity.HIGH,
        category="cio_lens",
        title="Too technical for executives",
        description="Slide 4 is too technical for executive CIO audience.",
        recommendation="Add executive summary highlighting business value.",
        confidence=0.92,
        action_type=ActionType.HUMAN_REVIEW_REQUIRED,
        evidence="Slide 4 lists technical infrastructure metrics rather than business ROI.",
    )

    merged = normalizer.normalize_and_deduplicate([f_content, f_cio])
    assert len(merged) == 1

    m = merged[0]
    assert m.slide == 4
    assert m.severity == Severity.HIGH  # Highest severity wins
    assert "content" in m.category and "cio_lens" in m.category  # Merged categories
    assert m.confidence == 0.92  # Highest confidence wins
    assert m.action_type == ActionType.HUMAN_REVIEW_REQUIRED





def test_weighted_scoring_model():
    """Verify that ReviewService calculates weighted score accurately."""
    svc = ReviewService()

    c_branding = AgentContract(agent_id="branding", status=AgentStatus.PASS, score=100)
    c_content = AgentContract(agent_id="content", status=AgentStatus.PASS, score=60)
    c_story = AgentContract(agent_id="story", status=AgentStatus.PASS, score=80)

    # Custom weights: branding 20%, content 40%, story 40%
    profile = {"weights": {"branding": 0.20, "content": 0.40, "story": 0.40}}
    score, status, dim_scores = svc._aggregate([c_branding, c_content, c_story], profile)

    # Expected score: (100*0.2 + 60*0.4 + 80*0.4) / (0.2 + 0.4 + 0.4) = 20 + 24 + 32 = 76
    assert score == 76
    assert status == "review"
    assert dim_scores["branding"] == 100
    assert dim_scores["content"] == 60
    assert dim_scores["story"] == 80


def test_visual_quality_rule_checks():
    """Verify that VisualQualityAgent performs rule-based visual inspections."""
    from services.ppt_service import PPTData, SlideData
    agent = VisualQualityAgent()

    slides = [
        SlideData(
            number=1,
            title="Overloaded Slide",
            bullets=["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "b9"],  # > 7 bullets
            body_text=" ".join(["word"] * 160),  # > 150 words
            speaker_notes="",
            has_image=False,
            layout_name="Title and Content",
            font_families=["Arial", "Calibri", "Comic Sans", "Verdana"],  # > 3 fonts
            background_color="#ffffff",
            placeholder_count=2,
            word_count=160,
            content_hash="abc",
        ),
        SlideData(
            number=2,
            title="",  # Missing title
            bullets=["Point"],
            body_text="Point",
            speaker_notes="",
            has_image=False,
            layout_name="Content",
            font_families=["Arial"],
            background_color="#ffffff",
            placeholder_count=1,
            word_count=1,
            content_hash="xyz",
        ),
    ]
    ppt = PPTData(filename="test.pptx", file_hash="123", slide_count=2, slides=slides)
    rule_findings = agent._run_rule_checks(ppt)

    # Rule findings should include Bullet overload, Word count density, Missing title, and Font variety
    rule_ids = [f.rule_id for f in rule_findings]
    assert "VIS-RULE-001" in rule_ids  # Bullet overload
    assert "VIS-RULE-002" in rule_ids  # Word count density
    assert "VIS-RULE-004" in rule_ids  # Missing slide title
    assert "VIS-RULE-005" in rule_ids  # Font variety


def test_fix_agent_recommendation_guidance():
    """Verify that FixAgent returns recommendation-only fix guides without direct file auto-fixes."""
    agent = FixAgent()
    finding = Finding(
        id="VIS-001",
        slide=2,
        severity=Severity.HIGH,
        category="visual_density",
        title="Dense slide layout",
        description="Slide 2 contains 10 bullets causing visual clutter.",
        recommendation="Split slide into 2 slides or group into 2 columns.",
        confidence=0.9,
        action_type=ActionType.RECOMMENDATION_ONLY,
    )
    context = {
        "findings": [finding],
        "original_filename": "deck.pptx",
    }
    # Mock LLM call to return recommendation guide
    agent._llm_call = lambda ctx, sys, usr, ver: {
        "summary": "Generated 1 recommendation guide.",
        "recommendations": [
            {
                "slide": 2,
                "finding_id": "VIS-001",
                "issue_title": "Dense slide layout",
                "fix_recommendation": "In PowerPoint, select the text box on Slide 2 and format into 2 columns.",
                "action_type": "RECOMMENDATION_ONLY"
            }
        ]
    }
    contract = agent.run(context)
    assert contract.status == AgentStatus.PASS
    assert "recommendations" in contract.metadata
    assert len(contract.metadata["recommendations"]) == 1
    assert contract.metadata["recommendations"][0]["action_type"] == "RECOMMENDATION_ONLY"


def test_content_agent_consistency_checks():
    """Verify that ContentAgent detects date and currency format inconsistencies across slides."""
    from services.ppt_service import PPTData, SlideData
    agent = ContentAgent()

    slides = [
        SlideData(
            number=1,
            title="Overview",
            bullets=["Delivery Date: 08/19/2026", "Project Budget: $100,000"],
            body_text="",
            speaker_notes="",
            has_image=False,
            layout_name="Title",
            font_families=["Arial"],
            background_color="#ffffff",
            placeholder_count=2,
            word_count=10,
            content_hash="s1",
        ),
        SlideData(
            number=2,
            title="Financials",
            bullets=["Milestone Date: August 19, 2026", "Project Cost: 100,000 USD"],
            body_text="",
            speaker_notes="",
            has_image=False,
            layout_name="Content",
            font_families=["Arial"],
            background_color="#ffffff",
            placeholder_count=1,
            word_count=10,
            content_hash="s2",
        ),
    ]
    ppt = PPTData(filename="deck.pptx", file_hash="111", slide_count=2, slides=slides)
    findings = agent._run_consistency_checks(ppt)

    rule_ids = [f.rule_id for f in findings]
    assert "CNT-CONSIST-001" in rule_ids  # Mixed date formats (MM/DD/YYYY vs Month DD, YYYY)
    assert "CNT-CONSIST-002" in rule_ids  # Mixed currency ($ vs USD)


