"""
InfoBeans-branded PPT builder for the Case Study Creator.

Design rules applied (from InfoBeans brand spec / rules.yaml):
  - Slide size  : 10 × 5.625 in  (16:9)
  - Fonts       : Lexend throughout
  - Colors      : brand palette only — brand_red #EA1B3D · charcoal #373742
                  case_study_green #214837 · case_study_navy #22225D
                  light_cream #FFF9ED · light_gray #E6E6ED
  - Eyebrow     : 12 pt · UPPERCASE · accent color · above heading
  - Title slide : 36 pt, cover background case_study_green
  - Body copy   : 16 pt (body_large preferred)
  - Bullets     : 14 pt (body_medium preferred)
  - Pagination  : bottom-left, 9 pt, charcoal #373742
  - Logo mark   : "InfoBeans" bottom-right text placeholder
"""
from __future__ import annotations

import io
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ── Brand palette (all values from rules.yaml) ────────────────────────────────
RED   = RGBColor(0xEA, 0x1B, 0x3D)   # brand_red
DARK  = RGBColor(0x37, 0x37, 0x42)   # charcoal_gray
MGRAY = RGBColor(0x67, 0x67, 0x75)   # medium_gray
LGRAY = RGBColor(0xE6, 0xE6, 0xED)   # light_gray
CREAM = RGBColor(0xFF, 0xF9, 0xED)   # light_cream  — content slide background
WHITE = RGBColor(0xFF, 0xFF, 0xFF)   # white
GREEN = RGBColor(0x21, 0x48, 0x37)   # case_study_green
NAVY  = RGBColor(0x22, 0x22, 0x5D)   # case_study_navy  — cover accent blocks

FONT = "Lexend"
W = Inches(10)
H = Inches(5.625)


# ── Low-level helpers ─────────────────────────────────────────────────────────

def _bg(slide, color: RGBColor):
    """Set the slide background fill colour."""
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _rect(slide, l, t, w, h, fill: RGBColor, line=False):
    shp = slide.shapes.add_shape(1, l, t, w, h)  # 1 = MSO rectangle
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line:
        shp.line.color.rgb = line
    else:
        shp.line.fill.background()
    return shp


def _txt(slide, text, l, t, w, h, size, color=WHITE, bold=False,
         align=PP_ALIGN.LEFT, wrap=True):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb


def _bullets(slide, items: list[str], l, t, w, h, size=15, color=DARK):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(4)
        run = p.add_run()
        run.text = f"•  {item}"
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.color.rgb = color
    return tb


# ── Footer (pagination + brand) ───────────────────────────────────────────────

def _footer(slide, num: int):
    _txt(slide, str(num),
         Inches(0.23), Inches(5.25), Inches(0.4), Inches(0.28),
         9, color=DARK, align=PP_ALIGN.LEFT)
    _txt(slide, "InfoBeans",
         Inches(8.9), Inches(5.25), Inches(1.0), Inches(0.28),
         9, color=MGRAY, align=PP_ALIGN.RIGHT)


# ── Slide builders ────────────────────────────────────────────────────────────

def _cover(slide, project_name: str, client_industry: str):
    # Background — case_study_green
    _rect(slide, 0, 0, W, H, GREEN)
    # Bottom strip — case_study_navy for contrast
    _rect(slide, 0, Inches(5.2), W, Inches(0.425), NAVY)
    # Left red accent bar
    _rect(slide, 0, 0, Inches(0.06), H, RED)
    # Top-right decorative block — case_study_navy
    _rect(slide, Inches(8.5), 0, Inches(1.5), Inches(1.0), NAVY)

    # "CASE STUDY" eyebrow
    _txt(slide, "CASE STUDY",
         Inches(0.5), Inches(1.1), Inches(7), Inches(0.4),
         12, color=RED)

    # Project name
    _txt(slide, project_name,
         Inches(0.5), Inches(1.6), Inches(8.2), Inches(1.6),
         36, color=WHITE)

    # Client / industry — white on dark green for legibility
    _txt(slide, client_industry,
         Inches(0.5), Inches(3.3), Inches(6), Inches(0.5),
         18, color=WHITE)

    # Prepared by — light_gray on dark green
    _txt(slide, "Prepared by InfoBeans",
         Inches(6.8), Inches(5.27), Inches(3.0), Inches(0.28),
         9, color=LGRAY, align=PP_ALIGN.RIGHT)


def _content_slide(slide, eyebrow: str, heading: str, body: str, num: int,
                   accent: RGBColor = RED):
    _bg(slide, CREAM)
    _rect(slide, 0, 0, W, Inches(0.055), accent)
    _txt(slide, eyebrow.upper(),
         Inches(0.55), Inches(0.15), Inches(8), Inches(0.35),
         12, color=accent)
    _txt(slide, heading,
         Inches(0.55), Inches(0.55), Inches(8.8), Inches(0.7),
         32, color=DARK)
    _rect(slide, Inches(0.55), Inches(1.32), Inches(8.9), Pt(1.2), LGRAY)
    _txt(slide, body,
         Inches(0.55), Inches(1.45), Inches(8.9), Inches(3.7),
         16, color=DARK, wrap=True)
    _footer(slide, num)


def _bullet_slide(slide, eyebrow: str, heading: str, items: list[str], num: int,
                  accent: RGBColor = RED):
    _bg(slide, CREAM)
    _rect(slide, 0, 0, W, Inches(0.055), accent)
    _txt(slide, eyebrow.upper(),
         Inches(0.55), Inches(0.15), Inches(8), Inches(0.35),
         12, color=accent)
    _txt(slide, heading,
         Inches(0.55), Inches(0.55), Inches(8.8), Inches(0.7),
         32, color=DARK)
    _rect(slide, Inches(0.55), Inches(1.32), Inches(8.9), Pt(1.2), LGRAY)
    _bullets(slide, items, Inches(0.55), Inches(1.45), Inches(8.9), Inches(3.7),
             size=14)
    _footer(slide, num)


def _tech_slide(slide, eyebrow: str, heading: str, items: list[str], num: int):
    _bg(slide, CREAM)
    _rect(slide, 0, 0, W, Inches(0.055), RED)
    _txt(slide, eyebrow.upper(),
         Inches(0.55), Inches(0.15), Inches(8), Inches(0.35),
         12, color=RED)
    _txt(slide, heading,
         Inches(0.55), Inches(0.55), Inches(8.8), Inches(0.7),
         32, color=DARK)
    _rect(slide, Inches(0.55), Inches(1.32), Inches(8.9), Pt(1.2), LGRAY)

    # Pill-style tech badges laid out in rows
    col_w = Inches(2.1)
    pad_l = Inches(0.55)
    top = Inches(1.5)
    for i, tech in enumerate(items[:12]):
        row, col = divmod(i, 4)
        l = pad_l + col * (col_w + Inches(0.15))
        t = top + row * Inches(0.65)
        pill = slide.shapes.add_shape(1, l, t, col_w, Inches(0.42))
        pill.fill.solid()
        pill.fill.fore_color.rgb = LGRAY
        pill.line.fill.background()
        tf = pill.text_frame
        tf.word_wrap = False
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = tech
        run.font.name = FONT
        run.font.size = Pt(13)
        run.font.color.rgb = DARK

    _footer(slide, num)


def _impact_slide(slide, headline: str, metrics: list[str], num: int):
    _bg(slide, CREAM)
    _rect(slide, 0, 0, W, Inches(0.055), GREEN)
    _txt(slide, "IMPACT",
         Inches(0.55), Inches(0.15), Inches(8), Inches(0.35),
         12, color=GREEN)
    _txt(slide, "Results & Business Impact",
         Inches(0.55), Inches(0.55), Inches(8.8), Inches(0.7),
         32, color=DARK)
    _rect(slide, Inches(0.55), Inches(1.32), Inches(8.9), Pt(1.2), LGRAY)

    # Headline metric callout — light_gray fill with green border
    box = slide.shapes.add_shape(1, Inches(0.55), Inches(1.45), Inches(8.9), Inches(0.62))
    box.fill.solid()
    box.fill.fore_color.rgb = LGRAY
    box.line.color.rgb = GREEN
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = headline
    run.font.name = FONT
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.color.rgb = GREEN

    # Metric bullets
    _bullets(slide, metrics, Inches(0.55), Inches(2.2), Inches(8.9), Inches(2.8),
             size=14, color=DARK)
    _footer(slide, num)


# ── Public entry point ────────────────────────────────────────────────────────

def build(cs: dict, project_name: str, client_industry: str) -> bytes:
    """Return the case study as a .pptx byte string."""
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    blank = prs.slide_layouts[6]  # Blank layout

    # Slide 1 — Cover (no page number)
    _cover(prs.slides.add_slide(blank), project_name, client_industry)

    # Slide 2 — Executive Summary
    _content_slide(
        prs.slides.add_slide(blank),
        "Executive Summary", "Executive Summary",
        cs.get("executive_summary", ""),
        num=2,
    )

    # Slide 3 — Business Challenges
    _bullet_slide(
        prs.slides.add_slide(blank),
        "Challenges", "Business Challenges",
        cs.get("business_challenges", []),
        num=3,
    )

    # Slide 4 — Solution
    sol = cs.get("solution", {})
    items = []
    if sol.get("overview"):
        items.append(sol["overview"])
    items += sol.get("key_points", [])
    _bullet_slide(
        prs.slides.add_slide(blank),
        "Solution", "Solution Implemented",
        items, num=4,
    )

    # Slide 5 — Technology Stack
    _tech_slide(
        prs.slides.add_slide(blank),
        "Technology", "Technology Stack",
        cs.get("technology_stack", []),
        num=5,
    )

    # Slide 6 — Results & Impact
    results = cs.get("results", {})
    _impact_slide(
        prs.slides.add_slide(blank),
        results.get("headline", ""),
        results.get("metrics", []),
        num=6,
    )

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
