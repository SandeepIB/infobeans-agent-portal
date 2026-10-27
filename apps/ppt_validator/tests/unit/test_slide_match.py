"""Unit tests for SlideMatchService and slide exclusions."""
import os
import pytest

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_platform.db")

from services.ppt_service import PPTData, PPTService, SlideData
from services.slide_match_service import SlideMatchService, DEFAULT_EXCLUDE_TEMPLATE_PATH
from agents.branding_agent import BrandingAgent


def _slide(number: int, title: str = "Title", fonts: list[str] | None = None) -> SlideData:
    return SlideData(
        number=number, title=title, bullets=[], body_text="body text",
        speaker_notes="", has_image=False, layout_name="Title and Content",
        font_families=fonts or ["Comic Sans MS"], background_color="#FF0000",
        placeholder_count=2, word_count=5, content_hash="hash_val",
        has_pagination=False, pagination_position=None, pagination_font=None,
        pagination_font_size=None, pagination_color=None, pagination_align=None,
        image_positions=[],
    )


def test_slide_match_with_exclude_slides_pptx():
    ppt_svc = PPTService()
    template_data = ppt_svc.extract(DEFAULT_EXCLUDE_TEMPLATE_PATH)
    match_svc = SlideMatchService(ppt_svc)

    exclusions = match_svc.find_matched_slides(template_data, DEFAULT_EXCLUDE_TEMPLATE_PATH)
    assert len(exclusions) == template_data.slide_count
    for exc in exclusions:
        assert exc["reason"] == "slide_design_match"
        assert exc["score"] >= 0.85
        assert exc["reference_template_id"] == "Exclude Slides.pptx"


def test_slide_match_unmatched():
    ppt_svc = PPTService()
    match_svc = SlideMatchService(ppt_svc)
    mock_ppt = PPTData(filename="unmatched.pptx", file_hash="123", slide_count=1, slides=[_slide(1, title="Unique Title Unmatched")])

    exclusions = match_svc.find_matched_slides(mock_ppt, DEFAULT_EXCLUDE_TEMPLATE_PATH)
    assert len(exclusions) == 0


def test_branding_agent_font_and_pagination_reported_on_excluded_slides():
    agent = BrandingAgent()
    slide_bad = _slide(2, fonts=["Comic Sans MS"]) # slide 2 to avoid title slide pagination bypass
    ppt = PPTData(filename="test.pptx", file_hash="hash", slide_count=2, slides=[slide_bad])

    # Slide 2 excluded for design/logo/background -> font & pagination findings MUST still be reported!
    ctx_ex = {"ppt_data": ppt, "profile": {}, "run_id": "r2", "excluded_slides": [2]}
    res = agent.run(ctx_ex)
    slide2_findings = [f for f in res.findings if f.slide == 2]

    # Verify font finding is reported
    font_findings = [f for f in slide2_findings if "font" in f.rule_id]
    assert len(font_findings) > 0

    # Verify pagination finding is reported
    pag_findings = [f for f in slide2_findings if "pagination" in f.rule_id]
    assert len(pag_findings) > 0

    # Verify logo & background color findings ARE skipped on slide 2
    logo_findings = [f for f in slide2_findings if "logo" in f.rule_id]
    assert len(logo_findings) == 0
    bg_findings = [f for f in slide2_findings if "color" in f.rule_id]
    assert len(bg_findings) == 0
