"""FROZEN — Legacy mechanical checks."""
from validator.models import Violation
from validator.rules import load_rules


def check_fonts(slides, rules: dict) -> list[Violation]:
    allowed = set(rules.get("branding", {}).get("allowed_fonts", []))
    violations = []
    for slide in slides:
        for font in slide.get("fonts", []):
            if allowed and font not in allowed:
                violations.append(Violation(
                    rule="font_check", slide=slide["number"],
                    message=f"Font '{font}' not in approved list.",
                    severity="MEDIUM", auto_fixable=True,
                ))
    return violations


def check_slide_count(slide_count: int, rules: dict) -> list[Violation]:
    template = rules.get("template", {})
    violations = []
    if slide_count < template.get("min_slides", 5):
        violations.append(Violation(rule="min_slides", slide=0,
                                    message=f"Too few slides: {slide_count}.", severity="HIGH"))
    if slide_count > template.get("max_slides", 30):
        violations.append(Violation(rule="max_slides", slide=0,
                                    message=f"Too many slides: {slide_count}.", severity="LOW"))
    return violations


def check_pagination(slides: list[dict], rules: dict) -> list[Violation]:
    pag_rules = rules.get("pagination", {})
    if not pag_rules.get("enabled", True):
        return []

    exclude_title = pag_rules.get("exclude_title_slide", True)
    target_left = pag_rules.get("left_pt", 21.96)
    target_top = pag_rules.get("top_pt", 376.0)
    pos_tol = pag_rules.get("position_tolerance_pt", 15.0)

    violations = []
    for slide in slides:
        slide_n = slide.get("number", 0) if isinstance(slide, dict) else getattr(slide, "number", 0)
        if exclude_title and slide_n == 1:
            continue
        has_pag = slide.get("has_pagination", False) if isinstance(slide, dict) else getattr(slide, "has_pagination", False)
        if not has_pag:
            violations.append(Violation(
                rule="pagination_missing", slide=slide_n,
                message=f"Slide {slide_n} is missing pagination/slide number.",
                severity="MEDIUM", auto_fixable=False,
            ))
        else:
            pos = slide.get("pagination_position") if isinstance(slide, dict) else getattr(slide, "pagination_position", None)
            if pos:
                if abs(pos.get("left", 0) - target_left) > pos_tol or abs(pos.get("top", 0) - target_top) > pos_tol:
                    violations.append(Violation(
                        rule="pagination_position", slide=slide_n,
                        message=f"Pagination on slide {slide_n} position ({pos.get('left')}pt, {pos.get('top')}pt) differs from expected ({target_left}pt, {target_top}pt).",
                        severity="MEDIUM", auto_fixable=False,
                    ))
    return violations


import math


def check_logo(slides: list, rules: dict) -> list[Violation]:
    logo_cfg = rules.get("logo", {})
    if not logo_cfg.get("enabled", True):
        return []

    req_slide_1 = logo_cfg.get("required_on_slide_1", True)
    req_all = logo_cfg.get("required_on_all_slides", False)
    target_left = logo_cfg.get("target_left_pt", 672.92)
    target_top = logo_cfg.get("target_top_pt", 369.99)
    target_w = logo_cfg.get("target_width_pt", 16.64)
    target_h = logo_cfg.get("target_height_pt", 16.64)
    pos_tol = logo_cfg.get("position_tolerance_pt", 15.0)
    size_tol = logo_cfg.get("size_tolerance_pt", 5.0)

    violations = []
    for slide in slides:
        slide_n = slide.get("number", 0) if isinstance(slide, dict) else getattr(slide, "number", 0)
        img_pos = slide.get("image_positions", []) if isinstance(slide, dict) else getattr(slide, "image_positions", [])
        is_slide_1 = (slide_n == 1)
        is_required = req_all or (req_slide_1 and is_slide_1)

        if not img_pos:
            if is_required:
                violations.append(Violation(
                    rule="logo_missing", slide=slide_n,
                    message=f"Slide {slide_n} is missing the brand logo in bottom-right corner.",
                    severity="HIGH", auto_fixable=False,
                ))
            continue

        best_img = None
        min_dist = float("inf")
        for img in img_pos:
            l, t = img.get("left", 0.0), img.get("top", 0.0)
            dist = math.hypot(l - target_left, t - target_top)
            if dist < min_dist:
                min_dist = dist
                best_img = img

        if best_img and min_dist <= pos_tol:
            w, h = best_img.get("width", 0.0), best_img.get("height", 0.0)
            if w > 0 and h > 0 and (abs(w - target_w) > size_tol or abs(h - target_h) > size_tol):
                violations.append(Violation(
                    rule="logo_size", slide=slide_n,
                    message=f"Slide {slide_n} logo size ({w}pt x {h}pt) differs from standard ({target_w}pt x {target_h}pt).",
                    severity="MEDIUM", auto_fixable=False,
                ))
        elif best_img and min_dist <= 150.0 and best_img.get("left", 0.0) >= 300.0 and best_img.get("top", 0.0) >= 180.0:
            violations.append(Violation(
                rule="logo_position", slide=slide_n,
                message=f"Slide {slide_n} logo is not placed in the bottom-right corner.",
                severity="HIGH", auto_fixable=False,
            ))
        elif is_required:
            violations.append(Violation(
                rule="logo_missing", slide=slide_n,
                message=f"Slide {slide_n} is missing the brand logo in bottom-right corner.",
                severity="HIGH", auto_fixable=False,
            ))
    return violations


