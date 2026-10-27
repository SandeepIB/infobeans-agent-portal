"""Unit tests for rule-based agents using mock PPTData."""
import os
import pytest

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_platform.db")

from services.ppt_service import PPTData, SlideData
from agents.branding_agent import BrandingAgent
from agents.template_agent import TemplateAgent


def _slide(number: int, title: str = "Title", fonts: list[str] | None = None,
           layout: str = "Title and Content", has_pagination: bool = True,
           pag_pos: dict | None = None, pag_font: str | None = "Lexend",
           pag_size: float | None = 9.0, pag_color: str | None = "#373742",
           pag_align: str | None = "left", has_image: bool = True) -> SlideData:
    br_img = [{"left": 672.92, "top": 369.99, "width": 16.64, "height": 16.64}]
    return SlideData(
        number=number, title=title, bullets=[], body_text="body",
        speaker_notes="", has_image=has_image, layout_name=layout,
        font_families=fonts or ["Lexend"], background_color=None,
        placeholder_count=2, word_count=5,
        content_hash="abc",
        has_pagination=has_pagination,
        pagination_position=pag_pos or {"left": 21.96, "top": 376.0, "width": 24.21, "height": 16.63},
        pagination_font=pag_font,
        pagination_font_size=pag_size,
        pagination_color=pag_color,
        pagination_align=pag_align,
        image_positions=br_img if has_image else [],
    )


def _ppt(slides: list[SlideData]) -> PPTData:
    return PPTData(filename="test.pptx", file_hash="hash", slide_count=len(slides), slides=slides)


def _ctx(ppt: PPTData) -> dict:
    return {"ppt_data": ppt, "profile": {}, "run_id": "test-run"}


class TestBrandingAgent:
    def test_approved_font_no_findings(self):
        agent = BrandingAgent()
        result = agent.run(_ctx(_ppt([_slide(1, fonts=["Lexend"])])))
        assert result.status == "completed"
        font_findings = [f for f in result.findings if "font" in f.title.lower()]
        assert len(font_findings) == 0

    def test_unapproved_font_raises_finding(self):
        agent = BrandingAgent()
        result = agent.run(_ctx(_ppt([_slide(1, fonts=["Comic Sans MS"])])))
        assert any("Comic Sans MS" in f.title for f in result.findings)

    def test_eyebrow_and_heading_case_validation(self):
        agent = BrandingAgent()
        # Slide with ALL CAPS title and non-uppercase eyebrow
        s = _slide(2, title="FIVE STAR ALLIANCE OVERVIEW", fonts=["Lexend"])
        s.eyebrow_text = "Case study"
        s.eyebrow_top = 100.0
        s.title_top = 50.0  # eyebrow below title
        result = agent.run(_ctx(_ppt([s])))

        rule_ids = [f.rule_id for f in result.findings]
        assert "branding_heading_case" in rule_ids
        assert "branding_eyebrow_case" in rule_ids
        assert "branding_eyebrow_position" in rule_ids

    def test_brand_spelling_email_ignored(self):
        agent = BrandingAgent()
        s = _slide(1, title="Contact Info")
        s.body_text = "Reach out to john.doe@infobeans.com or visit www.infobeans.com for details."
        result = agent.run(_ctx(_ppt([s])))
        spelling_findings = [f for f in result.findings if f.rule_id == "branding_spelling"]
        assert len(spelling_findings) == 0


class TestTemplateAgent:
    def test_too_few_slides(self):
        agent = TemplateAgent()
        ppt = _ppt([_slide(1, layout="Title Slide"), _slide(2)])
        result = agent.run(_ctx(ppt))
        assert any("few" in f.title.lower() for f in result.findings)

    def test_valid_slide_count(self):
        slides = [_slide(i, layout="Title Slide" if i == 1 else "Title and Content")
                  for i in range(1, 8)]
        agent = TemplateAgent()
        result = agent.run(_ctx(_ppt(slides)))
        count_findings = [f for f in result.findings if "slides" in f.title.lower()]
        assert len(count_findings) == 0
