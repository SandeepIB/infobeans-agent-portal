"""Unit tests for slide pagination validation in BrandingAgent and PPTService."""
import os
import pytest

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_platform.db")

from services.ppt_service import PPTData, SlideData, PPTService
from agents.branding_agent import BrandingAgent
from agents.base import ActionType


def _make_slide(number: int, has_pagination: bool = True,
                position: dict | None = None, font: str | None = "Lexend",
                size: float | None = 9.0, color: str | None = "#373742",
                align: str | None = "left") -> SlideData:
    return SlideData(
        number=number,
        title=f"Slide {number}",
        bullets=[],
        body_text="Test content",
        speaker_notes="",
        has_image=(number == 1),
        layout_name="Title Slide" if number == 1 else "Title and Content",
        font_families=["Lexend"],
        background_color=None,
        placeholder_count=2,
        word_count=5,
        content_hash=f"hash_{number}",
        has_pagination=has_pagination,
        pagination_position=position or {"left": 21.96, "top": 376.0, "width": 24.21, "height": 16.63},
        pagination_font=font,
        pagination_font_size=size,
        pagination_color=color,
        pagination_align=align,
    )


def _ctx(slides: list[SlideData]) -> dict:
    ppt = PPTData(filename="test_pagination.pptx", file_hash="hash123", slide_count=len(slides), slides=slides)
    return {"ppt_data": ppt, "profile": {}, "run_id": "test-pag-run"}


class TestPaginationValidation:
    def test_valid_pagination_no_findings(self):
        slides = [_make_slide(1), _make_slide(2)]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        assert result.status == "completed"
        pag_findings = [f for f in result.findings if "pagination" in f.rule_id]
        assert len(pag_findings) == 0

    def test_missing_pagination_raises_finding(self):
        slides = [_make_slide(1), _make_slide(2, has_pagination=False)]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        missing_findings = [f for f in result.findings if f.rule_id == "branding_pagination_missing"]
        assert len(missing_findings) == 1
        assert missing_findings[0].slide == 2
        assert missing_findings[0].action_type == ActionType.RECOMMENDATION_ONLY

    def test_title_slide_missing_pagination_excluded(self):
        # Slide 1 without pagination should be excluded from missing pagination check
        slides = [_make_slide(1, has_pagination=False), _make_slide(2, has_pagination=True)]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        missing_findings = [f for f in result.findings if f.rule_id == "branding_pagination_missing"]
        assert len(missing_findings) == 0

    def test_misplaced_pagination_raises_finding(self):
        wrong_pos = {"left": 150.0, "top": 150.0, "width": 50.0, "height": 20.0}
        slides = [_make_slide(1), _make_slide(2, position=wrong_pos)]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        pos_findings = [f for f in result.findings if f.rule_id == "branding_pagination_position"]
        assert len(pos_findings) == 1
        assert pos_findings[0].slide == 2
        assert "150.0" in pos_findings[0].description
        assert pos_findings[0].action_type == ActionType.RECOMMENDATION_ONLY

    def test_non_brand_pagination_font(self):
        slides = [_make_slide(1), _make_slide(2, font="Comic Sans MS")]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        font_findings = [f for f in result.findings if f.rule_id == "branding_pagination_font"]
        assert len(font_findings) == 1
        assert font_findings[0].slide == 2

    def test_incorrect_pagination_font_size(self):
        slides = [_make_slide(1), _make_slide(2, size=18.0)]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        size_findings = [f for f in result.findings if f.rule_id == "branding_pagination_size"]
        assert len(size_findings) == 1
        assert size_findings[0].slide == 2

    def test_incorrect_pagination_color(self):
        slides = [_make_slide(1), _make_slide(2, color="#FF0000")]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        color_findings = [f for f in result.findings if f.rule_id == "branding_pagination_color"]
        assert len(color_findings) == 1
        assert color_findings[0].slide == 2

    def test_incorrect_pagination_align(self):
        slides = [_make_slide(1), _make_slide(2, align="center")]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        align_findings = [f for f in result.findings if f.rule_id == "branding_pagination_align"]
        assert len(align_findings) == 1
        assert align_findings[0].slide == 2


class TestPaginationExtraction:
    def test_extract_pagination_check_pptx(self):
        svc = PPTService()
        data = svc.extract("slide_templates/Pagination check.pptx")
        assert data.slide_count >= 1
        s1 = data.slides[0]
        assert s1.has_pagination is True
        assert s1.pagination_position is not None
        assert abs(s1.pagination_position["left"] - 21.96) < 1.0
        assert abs(s1.pagination_position["top"] - 376.00) < 1.0
