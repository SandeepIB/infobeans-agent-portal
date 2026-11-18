"""Slide design match service — matches presentation slides against reference templates.
Primary default template: /var/www/html/Ib-ppt-validator/slide_templates/Exclude Slides.pptx
"""
from __future__ import annotations
import difflib
from pathlib import Path
from typing import Dict, List, Optional
import structlog

from services.ppt_service import PPTData, PPTService, SlideData

logger = structlog.get_logger()

DEFAULT_EXCLUDE_TEMPLATE_PATH = "/var/www/html/Ib-ppt-validator/slide_templates/Exclude Slides.pptx"


class SlideMatchService:
    def __init__(self, ppt_service: Optional[PPTService] = None):
        self.ppt_service = ppt_service or PPTService()
        self._template_cache: Dict[str, tuple[PPTData, float]] = {}

    def load_template(self, template_path: str | Path) -> Optional[PPTData]:
        path = Path(template_path)
        if not path.exists():
            logger.warning("template_not_found", path=str(path))
            return None
        key = str(path.resolve())
        mtime = path.stat().st_mtime
        if key in self._template_cache:
            cached_data, cached_mtime = self._template_cache[key]
            if cached_mtime == mtime:
                return cached_data

        try:
            ppt_data = self.ppt_service.extract(path)
            self._template_cache[key] = (ppt_data, mtime)
            return ppt_data
        except Exception as exc:
            logger.error("failed_to_load_template", path=key, error=str(exc))
            return None

    def find_matched_slides(
        self,
        ppt_data: PPTData,
        template_path: str | Path = DEFAULT_EXCLUDE_TEMPLATE_PATH,
        threshold: float = 0.70,
    ) -> List[dict]:
        """Compare slides in ppt_data against reference slides in template_path."""
        ref_ppt = self.load_template(template_path)
        if not ref_ppt or not ref_ppt.slides:
            return []

        template_name = Path(template_path).name
        exclusions: List[dict] = []

        for slide in ppt_data.slides:
            best_match_score = 0.0
            best_ref_slide_num = -1

            for ref_slide in ref_ppt.slides:
                score = self.compute_similarity(slide, ref_slide)
                if score > best_match_score:
                    best_match_score = score
                    best_ref_slide_num = ref_slide.number

            if best_match_score >= threshold:
                exclusions.append({
                    "slide_number": slide.number,
                    "reason": "slide_design_match",
                    "detail": f"Matches {template_name} slide {best_ref_slide_num} with score {round(best_match_score, 2)}",
                    "score": round(best_match_score, 2),
                    "reference_template_id": template_name,
                    "reference_slide_number": best_ref_slide_num,
                    "scope": "design_agents",
                    "excluded_agents": ["template", "branding"],
                })

        return exclusions

    def compute_similarity(self, slide1: SlideData, slide2: SlideData) -> float:
        """Compute visual and structural similarity score [0.0, 1.0] between two slides."""
        # 1. Exact content hash match
        if slide1.content_hash and slide1.content_hash == slide2.content_hash:
            if slide1.body_text or slide1.title:
                return 1.0

        scores = []
        weights = []

        # 2. Slide Layout Name (High weight: 0.35 for design matching)
        if slide1.layout_name and slide2.layout_name:
            layout_sim = 1.0 if slide1.layout_name == slide2.layout_name else 0.0
            scores.append(layout_sim)
            weights.append(0.35)
        else:
            scores.append(0.5)
            weights.append(0.35)

        # 3. Image positions & count similarity (High weight: 0.25)
        img1_pos = getattr(slide1, "image_positions", [])
        img2_pos = getattr(slide2, "image_positions", [])
        img1_cnt = len(img1_pos)
        img2_cnt = len(img2_pos)
        if img1_cnt == 0 and img2_cnt == 0:
            scores.append(1.0)
            weights.append(0.25)
        elif img1_cnt == 0 or img2_cnt == 0:
            scores.append(0.0)
            weights.append(0.25)
        else:
            # Calculate position match ratio
            matches = 0
            for pos1 in img1_pos:
                l1, t1 = pos1.get("left", 0.0), pos1.get("top", 0.0)
                for pos2 in img2_pos:
                    l2, t2 = pos2.get("left", 0.0), pos2.get("top", 0.0)
                    if abs(l1 - l2) <= 25.0 and abs(t1 - t2) <= 25.0:
                        matches += 1
                        break
            max_cnt = max(img1_cnt, img2_cnt)
            scores.append(matches / max_cnt if max_cnt > 0 else 0.0)
            weights.append(0.25)

        # 4. Placeholder count & structure (Medium weight: 0.15)
        max_ph = max(slide1.placeholder_count, slide2.placeholder_count, 1)
        ph_diff = abs(slide1.placeholder_count - slide2.placeholder_count)
        ph_sim = max(0.0, 1.0 - (ph_diff / max_ph))
        scores.append(ph_sim)
        weights.append(0.15)

        # 5. Background Color & Fonts (Medium weight: 0.15)
        bg_sim = 1.0 if (slide1.background_color == slide2.background_color) else 0.0
        scores.append(bg_sim)
        weights.append(0.15)

        # 6. Text Content & Title similarity (Low weight: 0.10 for design template matching)
        text1 = (slide1.title + " " + slide1.body_text).strip().lower()
        text2 = (slide2.title + " " + slide2.body_text).strip().lower()
        if text1 and text2:
            seq_ratio = difflib.SequenceMatcher(None, text1, text2).ratio()
            scores.append(seq_ratio)
            weights.append(0.10)
        elif not text1 and not text2:
            scores.append(1.0)
            weights.append(0.10)
        else:
            scores.append(0.0)
            weights.append(0.10)

        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        final_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        return final_score
