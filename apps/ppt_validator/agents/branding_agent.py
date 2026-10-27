"""Branding agent — 4 mechanical checks: font, color, logo, pagination.
All allowed values come from rules.yaml via RuleService — never hardcoded.
"""
from __future__ import annotations
import math
from agents.base import AgentContract, ReviewAgent, Finding, Severity, ActionType
from services.rule_service import RuleService
from agents.registry import register_agent

_rule_svc = RuleService()


class BrandingAgent(ReviewAgent):
    agent_id = "branding"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]
            rules = _rule_svc.get_rules("branding")
            findings: list[Finding] = []

            allowed_fonts  = {r["value"] for r in rules if r.get("type") == "allowed_font"}
            allowed_colors = {r["value"].upper() for r in rules if r.get("type") == "allowed_color"}
            logo_phash     = next((r["value"] for r in rules if r.get("type") == "logo_phash"), None)
            logo_tolerance = int(next((r["value"] for r in rules if r.get("type") == "logo_tolerance"), 10))

            excluded_slides = set(context.get("excluded_slides", []))

            # Build the set of special-design slides exempt from pagination/logo checks.
            # These are: slide 1 (cover), section dividers, visual/dark design slides, and
            # any slides already marked as excluded by the SlideMatchService.
            special_design_slides: set[int] = {1} | excluded_slides
            for _s in ppt.slides:
                if self._is_special_design_slide(_s):
                    special_design_slides.add(_s.number)

            # Check 0: Aspect ratio / size (16:9 widescreen requirement)
            if getattr(ppt, "is_16_9", True) is False:
                ratio_val = getattr(ppt, "aspect_ratio", 1.33)
                findings.append(Finding(
                    slide=0, severity=Severity.HIGH,
                    category="branding", title="Non-compliant slide aspect ratio (4:3 or odd size)",
                    description=f"Presentation uses non-standard aspect ratio {ratio_val} ({getattr(ppt, 'slide_width_in', 0)} in x {getattr(ppt, 'slide_height_in', 0)} in). Brand guidelines mandate 16:9 widescreen (10 in x 5.625 in).",
                    recommendation="Convert presentation layout to 16:9 widescreen (10 in x 5.625 in / 25.4 cm x 14.29 cm).",
                    confidence=1.0, action_type=ActionType.HUMAN_APPROVAL,
                    rule_id="branding_aspect_ratio",
                ))

            for slide in ppt.slides:
                # Check 1: font compliance (runs on all slides, including excluded slides)
                # A font passes if it exactly matches or starts with an allowed font family
                # e.g. "Lexend Light", "Lexend SemiBold" all pass when "Lexend" is allowed
                for font in slide.font_families:
                    if allowed_fonts and not any(
                        font == af or font.startswith(af + " ") for af in allowed_fonts
                    ):
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.MEDIUM,
                            category="branding", title=f"Non-brand font: {font}",
                            description=f"Font '{font}' is not in the approved brand font list. Expected: {', '.join(sorted(allowed_fonts))}.",
                            recommendation=f"Replace '{font}' with the approved font: {', '.join(sorted(allowed_fonts))}.",
                            confidence=1.0, action_type=ActionType.AUTO_FIX,
                            rule_id="branding_font",
                        ))

                # Check 2: background color & custom ground restrictions
                if slide.number in excluded_slides:
                    continue
                if slide.background_color and allowed_colors:
                    bg = slide.background_color.upper()
                    if bg not in allowed_colors:
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.HIGH,
                            category="branding", title="Unapproved background color",
                            description=f"Slide {slide.number} uses background color {bg} which is not in the approved brand palette.",
                            recommendation="Use an approved brand background color (Light Cream #FFF9ED, White #FFFFFF, Charcoal #373742).",
                            confidence=0.9, action_type=ActionType.HUMAN_APPROVAL,
                            rule_id="branding_color",
                        ))

            # Check 3: logo presence, position, and size compliance
            logo_enabled = next((r["value"].lower() == "true" for r in rules if r.get("type") == "logo_enabled"), True)
            logo_req_slide_1 = next((r["value"].lower() == "true" for r in rules if r.get("type") in ("logo_required_slide_1", "logo_required_on_slide_1")), True)
            logo_req_all = next((r["value"].lower() == "true" for r in rules if r.get("type") in ("logo_required_all_slides", "logo_required_all")), False)
            logo_target_left = float(next((r["value"] for r in rules if r.get("type") == "logo_target_left_pt"), 672.92))
            logo_target_top = float(next((r["value"] for r in rules if r.get("type") == "logo_target_top_pt"), 369.99))
            logo_target_width = float(next((r["value"] for r in rules if r.get("type") == "logo_target_width_pt"), 16.64))
            logo_target_height = float(next((r["value"] for r in rules if r.get("type") == "logo_target_height_pt"), 16.64))
            logo_pos_tol = float(next((r["value"] for r in rules if r.get("type") == "logo_position_tolerance_pt"), 15.0))
            logo_size_tol = float(next((r["value"] for r in rules if r.get("type") == "logo_size_tolerance_pt"), 5.0))

            if ppt.slides and logo_enabled:
                for slide in ppt.slides:
                    # Skip slides that are excluded by SlideMatchService or identified as special design
                    if slide.number in special_design_slides:
                        continue
                    img_positions = getattr(slide, "image_positions", [])
                    is_slide_1 = (slide.number == 1)
                    is_required = logo_req_all or (logo_req_slide_1 and is_slide_1)

                    if not img_positions:
                        if is_required:
                            findings.append(Finding(
                                slide=slide.number, severity=Severity.HIGH,
                                category="branding", title="Missing logo",
                                description=f"Slide {slide.number} does not have the brand logo in the bottom-right corner.",
                                recommendation=f"Add the brand logo at (left: {logo_target_left}pt, top: {logo_target_top}pt, width: {logo_target_width}pt, height: {logo_target_height}pt).",
                                confidence=0.9, action_type=ActionType.HUMAN_APPROVAL,
                                rule_id="branding_logo_missing",
                            ))
                        continue

                    best_img = None
                    min_dist = float("inf")
                    for img in img_positions:
                        l, t = img.get("left", 0.0), img.get("top", 0.0)
                        dist = math.hypot(l - logo_target_left, t - logo_target_top)
                        if dist < min_dist:
                            min_dist = dist
                            best_img = img

                    if best_img and min_dist <= logo_pos_tol:
                        w, h = best_img.get("width", 0.0), best_img.get("height", 0.0)
                        if w > 0 and h > 0 and (abs(w - logo_target_width) > logo_size_tol or abs(h - logo_target_height) > logo_size_tol):
                            findings.append(Finding(
                                slide=slide.number, severity=Severity.MEDIUM,
                                category="branding", title="Incorrect logo dimensions",
                                description=f"Logo size on slide {slide.number} is ({w}pt x {h}pt). Expected size: ({logo_target_width}pt x {logo_target_height}pt).",
                                recommendation=f"Resize logo to ({logo_target_width}pt x {logo_target_height}pt).",
                                confidence=0.85, action_type=ActionType.HUMAN_APPROVAL,
                                rule_id="branding_logo_size",
                            ))
                    elif best_img and min_dist <= 150.0 and best_img.get("left", 0.0) >= 300.0 and best_img.get("top", 0.0) >= 180.0:
                        l_val = best_img.get("left", 0.0)
                        t_val = best_img.get("top", 0.0)
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.HIGH,
                            category="branding", title="Logo incorrectly positioned",
                            description=f"Logo on slide {slide.number} is positioned at (left: {l_val}pt, top: {t_val}pt). Expected position: (left: {logo_target_left}pt, top: {logo_target_top}pt).",
                            recommendation=f"Reposition logo to (left: {logo_target_left}pt, top: {logo_target_top}pt).",
                            confidence=0.85, action_type=ActionType.HUMAN_APPROVAL,
                            rule_id="branding_logo_position",
                        ))
                    elif is_required:
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.HIGH,
                            category="branding", title="Missing logo",
                            description=f"Slide {slide.number} does not have the brand logo in the bottom-right corner.",
                            recommendation=f"Add the brand logo at (left: {logo_target_left}pt, top: {logo_target_top}pt, width: {logo_target_width}pt, height: {logo_target_height}pt).",
                            confidence=0.9, action_type=ActionType.HUMAN_APPROVAL,
                            rule_id="branding_logo_missing",
                        ))

            # Check 4: Pagination compliance (presence, position, font, size, color, align)
            pag_enabled = next((r["value"].lower() == "true" for r in rules if r.get("type") == "pagination_enabled"), True)
            pag_exclude_title = next((r["value"].lower() == "true" for r in rules if r.get("type") == "pagination_exclude_title"), True)
            target_left = float(next((r["value"] for r in rules if r.get("type") == "pagination_left_pt"), 21.96))
            target_top = float(next((r["value"] for r in rules if r.get("type") == "pagination_top_pt"), 376.00))
            pos_tolerance = float(next((r["value"] for r in rules if r.get("type") in ("pagination_tolerance_pt", "pagination_position_tolerance_pt")), 5.0))
            expected_font = next((r["value"] for r in rules if r.get("type") == "pagination_font"), "Lexend")
            expected_font_size = float(next((r["value"] for r in rules if r.get("type") == "pagination_font_size"), 9.0))
            expected_color = next((r["value"].upper() for r in rules if r.get("type") == "pagination_color"), "#373742")
            expected_align = next((r["value"].lower() for r in rules if r.get("type") == "pagination_align"), "left")

            for slide in ppt.slides:
                # Skip title slide (always) and special design slides for pagination
                if slide.number in special_design_slides:
                    continue

                if pag_enabled and not getattr(slide, "has_pagination", False):
                    findings.append(Finding(
                        slide=slide.number, severity=Severity.MEDIUM,
                        category="branding", title="Missing slide pagination",
                        description=f"Slide {slide.number} does not have slide pagination/numbering.",
                        recommendation=f"Add slide pagination at position (left: {target_left}pt, top: {target_top}pt).",
                        confidence=0.95, action_type=ActionType.RECOMMENDATION_ONLY,
                        rule_id="branding_pagination_missing",
                    ))
                elif getattr(slide, "has_pagination", False):
                    pos = getattr(slide, "pagination_position", None)
                    if pos:
                        left_diff = abs(pos.get("left", 0.0) - target_left)
                        top_diff = abs(pos.get("top", 0.0) - target_top)
                        if left_diff > pos_tolerance or top_diff > pos_tolerance:
                            findings.append(Finding(
                                slide=slide.number, severity=Severity.MEDIUM,
                                category="branding", title="Incorrect pagination position",
                                description=f"Pagination on slide {slide.number} is positioned at (left: {pos.get('left')}pt, top: {pos.get('top')}pt). Expected position: (left: {target_left}pt, top: {target_top}pt).",
                                recommendation=f"Reposition slide pagination to (left: {target_left}pt, top: {target_top}pt).",
                                confidence=0.9, action_type=ActionType.RECOMMENDATION_ONLY,
                                rule_id="branding_pagination_position",
                            ))

                    p_font = getattr(slide, "pagination_font", None)
                    if p_font:
                        if not (p_font == expected_font or p_font.startswith(expected_font + " ") or (allowed_fonts and any(p_font == af or p_font.startswith(af + " ") for af in allowed_fonts))):
                            findings.append(Finding(
                                slide=slide.number, severity=Severity.LOW,
                                category="branding", title=f"Non-brand pagination font: {p_font}",
                                description=f"Pagination font '{p_font}' on slide {slide.number} does not match approved brand font '{expected_font}'.",
                                recommendation=f"Change pagination font to approved font '{expected_font}'.",
                                confidence=0.9, action_type=ActionType.RECOMMENDATION_ONLY,
                                rule_id="branding_pagination_font",
                            ))

                    p_size = getattr(slide, "pagination_font_size", None)
                    if p_size and abs(p_size - expected_font_size) > 3.0:
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.LOW,
                            category="branding", title="Incorrect pagination font size",
                            description=f"Pagination font size on slide {slide.number} is {p_size}pt. Expected: {expected_font_size}pt.",
                            recommendation=f"Set pagination font size to {expected_font_size}pt.",
                            confidence=0.85, action_type=ActionType.RECOMMENDATION_ONLY,
                            rule_id="branding_pagination_size",
                        ))

                    p_color = getattr(slide, "pagination_color", None)
                    if p_color and p_color.upper() != expected_color and (allowed_colors and p_color.upper() not in allowed_colors):
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.LOW,
                            category="branding", title="Non-brand pagination color",
                            description=f"Pagination color '{p_color}' on slide {slide.number} does not match brand color '{expected_color}'.",
                            recommendation=f"Set pagination font color to approved brand color '{expected_color}'.",
                            confidence=0.85, action_type=ActionType.RECOMMENDATION_ONLY,
                            rule_id="branding_pagination_color",
                        ))

                    p_align = getattr(slide, "pagination_align", None)
                    if p_align and p_align.lower() not in (expected_align, "right", "left"):
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.LOW,
                            category="branding", title="Incorrect pagination alignment",
                            description=f"Pagination alignment on slide {slide.number} is '{p_align}'. Expected: '{expected_align}'.",
                            recommendation=f"Set pagination text alignment to '{expected_align}'.",
                            confidence=0.85, action_type=ActionType.RECOMMENDATION_ONLY,
                            rule_id="branding_pagination_align",
                        ))

            # Check 5: Heading & Eyebrow Casing & Positioning rules
            heading_case = next((r["value"].lower() for r in rules if r.get("type") == "heading_case"), "sentence")
            eyebrow_case = next((r["value"].lower() for r in rules if r.get("type") == "eyebrow_case"), "uppercase")
            eyebrow_pos  = next((r["value"].lower() for r in rules if r.get("type") == "eyebrow_position"), "above_header")

            for slide in ppt.slides:
                if slide.number in excluded_slides:
                    continue

                # 5a. Heading case check (Sentence Case)
                if slide.title and heading_case == "sentence":
                    title_clean = slide.title.strip()
                    alpha_words = [w for w in title_clean.split() if any(c.isalpha() for c in w)]
                    if title_clean.isupper() and len(alpha_words) > 1:
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.MEDIUM,
                            category="branding", title="Non-compliant heading casing (ALL CAPS)",
                            description=f"Slide {slide.number} heading '{slide.title}' is in ALL CAPS. Brand rules mandate sentence case.",
                            recommendation=f"Convert heading to sentence case (e.g. '{title_clean.capitalize()}').",
                            confidence=0.9, action_type=ActionType.AUTO_FIX,
                            rule_id="branding_heading_case",
                        ))

                # 5b. Eyebrow case check (Uppercase / ALL CAPS)
                eyebrow_txt = getattr(slide, "eyebrow_text", None)
                if eyebrow_txt and eyebrow_case == "uppercase":
                    eyebrow_clean = eyebrow_txt.strip()
                    if not eyebrow_clean.isupper() and any(c.isalpha() for c in eyebrow_clean):
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.MEDIUM,
                            category="branding", title="Non-compliant eyebrow casing",
                            description=f"Eyebrow header on slide {slide.number} ('{eyebrow_txt}') is not in ALL CAPS. Eyebrow headers must be in uppercase per brand rules.",
                            recommendation=f"Convert eyebrow header to uppercase (e.g. '{eyebrow_clean.upper()}').",
                            confidence=0.9, action_type=ActionType.AUTO_FIX,
                            rule_id="branding_eyebrow_case",
                        ))

                # 5c. Eyebrow position check (Above Header)
                e_top = getattr(slide, "eyebrow_top", None)
                t_top = getattr(slide, "title_top", None)
                if eyebrow_txt and eyebrow_pos == "above_header":
                    if e_top is not None and t_top is not None and e_top > t_top:
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.HIGH,
                            category="branding", title="Eyebrow positioned below heading",
                            description=f"Eyebrow header on slide {slide.number} sits below the main title. Brand rules require eyebrow to sit above the heading.",
                            recommendation="Reposition the eyebrow text box above the slide title.",
                            confidence=0.95, action_type=ActionType.HUMAN_APPROVAL,
                            rule_id="branding_eyebrow_position",
                        ))

                # Check 6: Leftover template placeholders & unfinished slides (§9)
                placeholder_patterns = [r["value"].lower() for r in rules if r.get("type") == "placeholder_pattern"]
                if not placeholder_patterns:
                    placeholder_patterns = [
                        "add title here", "add copy here as needed", "add subhead",
                        "lorem ipsum", "example slide", "do not use", "body text"
                    ]
                slide_text_lower = f"{slide.title} {slide.body_text} {' '.join(slide.bullets)}".lower()
                for ph in placeholder_patterns:
                    if ph in slide_text_lower:
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.HIGH,
                            category="branding", title="Leftover template placeholder text",
                            description=f"Slide {slide.number} contains leftover template placeholder text ('{ph}').",
                            recommendation="Remove placeholder text or replace with real content.",
                            confidence=0.95, action_type=ActionType.HUMAN_APPROVAL,
                            rule_id="branding_leftover_placeholder",
                        ))
                        break

                # Check 7: Missing source citation for statistics & data charts (§9)
                citation_keywords = [r["value"].lower() for r in rules if r.get("type") == "source_citation_keyword"]
                if not citation_keywords:
                    citation_keywords = ["%", "billion", "million", "tn", "$", "usd", "revenue"]

                if any(kw in slide_text_lower for kw in citation_keywords):
                    if "source:" not in slide_text_lower and "source" not in slide_text_lower:
                        findings.append(Finding(
                            slide=slide.number, severity=Severity.MEDIUM,
                            category="branding", title="Missing source citation for data/statistic",
                            description=f"Slide {slide.number} contains statistics or financial metrics but lacks a 'Source: ...' footnote citation.",
                            recommendation="Add a 6–8 pt footnote citation at the bottom-left of the slide citing the data source.",
                            confidence=0.85, action_type=ActionType.RECOMMENDATION_ONLY,
                            rule_id="branding_missing_source_citation",
                        ))

                # Check 8: Incorrect brand name spelling (§9)
                forbidden_spellings = [r["value"] for r in rules if r.get("type") == "forbidden_brand_spelling"]
                if not forbidden_spellings:
                    forbidden_spellings = ["Infobeans", "infoBeans", "INFOBEANS", "infobeans"]
                for word in slide_text_lower.split():
                    clean_word = word.strip(",.!:;()'\"")
                    if clean_word in [fs.lower() for fs in forbidden_spellings]:
                        # Check original casing in title/body
                        orig_text = f"{slide.title} {slide.body_text}"
                        for w in orig_text.split():
                            clean_w = w.strip(",.!:;()'\"")
                            # Ignore emails (@) and web domain URLs (infobeans.com, www.)
                            if "@" in clean_w or "infobeans.com" in clean_w.lower() or "www." in clean_w.lower():
                                continue
                            if clean_w in ["Infobeans", "infoBeans", "INFOBEANS", "infobeans"]:
                                findings.append(Finding(
                                    slide=slide.number, severity=Severity.LOW,
                                    category="branding", title="Incorrect brand name capitalization",
                                    description=f"Slide {slide.number} contains incorrect brand spelling '{clean_w}'. The official brand name is 'InfoBeans'.",
                                    recommendation="Capitalize brand name as 'InfoBeans' (except in email addresses and URLs).",
                                    confidence=0.9, action_type=ActionType.AUTO_FIX,
                                    rule_id="branding_spelling",
                                ))
                                break
                        break

            score = max(0, 100 - len(findings) * 10)
            return AgentContract(
                agent_id=self.agent_id, status="completed", score=score,
                findings=findings,
                summary=f"{len(findings)} branding issue(s) found.",
            )
        except Exception as exc:
            return self._failed(str(exc))


    @staticmethod
    def _is_special_design_slide(slide) -> bool:
        """
        Heuristic: return True if a slide is a 'special design' slide that should be
        exempt from pagination and logo placement checks.

        A slide is considered special/design if it meets ANY of the following:
          1. Its layout name contains a known design-only keyword.
          2. It has a non-white, non-cream background color (coloured/dark background).
          3. It has very few words (≤ 5) AND contains at least one image —
             indicating a visual-only design slide.
          4. It has zero words and no bullets (completely image/graphic slide).
        """
        # 1. Layout name heuristic
        SPECIAL_LAYOUT_KEYWORDS = {
            "cover", "title", "divider", "section", "quote",
            "testimonial", "case study", "closing", "blank", "end",
            "thank", "full bleed", "image only", "visual",
        }
        layout_name = (getattr(slide, "layout_name", "") or "").lower()
        if any(kw in layout_name for kw in SPECIAL_LAYOUT_KEYWORDS):
            return True

        # 2. Non-standard background colour (not white #FFFFFF or cream #FFF9ED / #FFF3D4)
        STANDARD_BG = {"#FFFFFF", "#FFF9ED", "#FFF3D4", "#F5F5F5", "#E6E6ED", None}
        bg = getattr(slide, "background_color", None)
        if bg and bg.upper() not in {c.upper() if c else c for c in STANDARD_BG}:
            return True

        # 3. Visual-only design slide: very few words + has an image
        word_count = getattr(slide, "word_count", 0)
        has_image = getattr(slide, "has_image", False)
        has_bullets = bool(getattr(slide, "bullets", []))
        if word_count <= 5 and has_image and not has_bullets:
            return True

        # 4. Completely empty slide (no text at all)
        body_text = (getattr(slide, "body_text", "") or "").strip()
        title = (getattr(slide, "title", "") or "").strip()
        if not body_text and not title and not has_bullets:
            return True

        return False


register_agent("branding", BrandingAgent, stage="extraction", execution_mode="parallel",
               cacheability="full")
