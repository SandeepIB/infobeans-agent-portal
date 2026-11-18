"""Unit tests for bottom-right logo presence, position, and size validation."""
import os
import pytest

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///test_platform.db")

from services.ppt_service import PPTData, SlideData, PPTService
from agents.branding_agent import BrandingAgent


def _make_slide(number: int, has_image: bool = True, image_positions: list[dict] | None = None) -> SlideData:
    br_pos = [{"left": 672.92, "top": 369.99, "width": 16.64, "height": 16.64}]
    img_pos = image_positions if image_positions is not None else (br_pos if has_image else [])
    return SlideData(
        number=number,
        title=f"Slide {number}",
        bullets=[],
        body_text="Test body",
        speaker_notes="",
        has_image=has_image or len(img_pos) > 0,
        layout_name="Title Slide" if number == 1 else "Title and Content",
        font_families=["Lexend"],
        background_color=None,
        placeholder_count=2,
        word_count=5,
        content_hash=f"hash_{number}",
        has_pagination=True,
        pagination_position={"left": 21.96, "top": 376.0, "width": 24.21, "height": 16.63},
        pagination_font="Lexend",
        pagination_font_size=9.0,
        pagination_color="#373742",
        pagination_align="left",
        image_positions=img_pos,
    )


def _ctx(slides: list[SlideData]) -> dict:
    ppt = PPTData(filename="test_logo.pptx", file_hash="hash123", slide_count=len(slides), slides=slides)
    return {"ppt_data": ppt, "profile": {}, "run_id": "test-logo-run"}


class TestLogoValidation:
    def test_valid_bottom_right_logo_no_findings(self):
        slides = [_make_slide(1, has_image=True), _make_slide(2, has_image=True)]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        logo_findings = [f for f in result.findings if "logo" in f.rule_id]
        assert len(logo_findings) == 0

    def test_missing_logo_on_slide_2(self):
        slides = [_make_slide(1, has_image=True), _make_slide(2, has_image=False, image_positions=[])]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        logo_missing = [f for f in result.findings if f.rule_id == "branding_logo_missing"]
        assert len(logo_missing) == 1
        assert logo_missing[0].slide == 2

    def test_misplaced_logo(self):
        misplaced_pos = [{"left": 600.0, "top": 300.0, "width": 16.64, "height": 16.64}]
        slides = [_make_slide(1, has_image=True), _make_slide(2, has_image=True, image_positions=misplaced_pos)]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        logo_pos_findings = [f for f in result.findings if f.rule_id == "branding_logo_position"]
        assert len(logo_pos_findings) == 1
        assert logo_pos_findings[0].slide == 2

    def test_incorrect_logo_size(self):
        wrong_size = [{"left": 672.92, "top": 369.99, "width": 50.0, "height": 50.0}]
        slides = [_make_slide(1, has_image=True), _make_slide(2, has_image=True, image_positions=wrong_size)]
        agent = BrandingAgent()
        result = agent.run(_ctx(slides))
        logo_size_findings = [f for f in result.findings if f.rule_id == "branding_logo_size"]
        assert len(logo_size_findings) == 1
        assert logo_size_findings[0].slide == 2


class TestLogoExtraction:
    def test_extract_logo_check_pptx(self):
        svc = PPTService()
        data = svc.extract("slide_templates/Logo_check.pptx")
        assert data.slide_count >= 1
        s1 = data.slides[0]
        assert s1.has_image is True
        assert len(s1.image_positions) > 0
        img = s1.image_positions[0]
        assert abs(img["left"] - 672.92) < 2.0
        assert abs(img["top"] - 369.99) < 2.0
        assert abs(img["width"] - 16.64) < 2.0
        assert abs(img["height"] - 16.64) < 2.0
