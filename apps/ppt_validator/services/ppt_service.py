"""PPT extraction service — produces structured slide representations.
Never sends raw XML or binary to LLMs.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import re

from pptx import Presentation
from pptx.util import Pt
from pptx.enum.text import PP_ALIGN


@dataclass
class TableColumnData:
    """Per-column metadata extracted from a PPTX table."""
    index: int
    header_text: str
    # Alignment values: 'left', 'right', 'center', 'justify', 'unknown'
    data_alignment: str          # dominant alignment of data cells in this column
    header_alignment: str        # alignment of the header cell
    sample_values: list[str]     # first 5 data cell texts
    number_formats: list[str]    # detected format tokens (e.g. 'currency_short', 'currency_long', 'percent_int', 'percent_float')
    font_names: list[str]        # distinct font families used in this column
    width_emu: int = 0           # column width in EMUs (Rule 3)
    header_word_count: int = 0   # word count of header text (Rule 8)
    has_mixed_number_format: bool = False  # True when column mixes $2.4M style with $1,850,000 style
    header_matches_data_align: bool = True  # False if header align ≠ data align


@dataclass
class TableData:
    """Structured metadata for a single table shape on a slide."""
    shape_name: str
    row_count: int
    col_count: int
    has_header_row: bool
    columns: list[TableColumnData]
    has_heavy_borders: bool       # True if all cells have uniform thick borders (spreadsheet feel)
    has_many_dense_cells: bool    # True if majority of cells have ≥ 3 lines of text
    font_names: list[str]         # all distinct fonts used in the table
    misaligned_columns: list[int] # 0-based column indices where data alignment seems wrong
    has_uniform_column_widths: bool = False   # Rule 3: all columns same width (no density consideration)
    unique_cell_fill_colors: int = 0          # Rule 10: count of distinct non-white/none fill colors
    verbose_header_columns: list[int] = field(default_factory=list)  # Rule 8: 0-based cols with verbose headers (>4 words)


@dataclass
class SlideData:
    number: int
    title: str
    bullets: list[str]
    body_text: str
    speaker_notes: str
    has_image: bool
    layout_name: str
    font_families: list[str]
    background_color: str | None
    placeholder_count: int
    word_count: int
    content_hash: str
    has_pagination: bool = False
    pagination_position: dict | None = None  # {"left": float, "top": float, "width": float, "height": float} in Pt
    pagination_font: str | None = None
    pagination_font_size: float | None = None
    pagination_color: str | None = None
    pagination_align: str | None = None
    image_positions: list[dict] = field(default_factory=list)
    eyebrow_text: str | None = None
    eyebrow_top: float | None = None
    title_top: float | None = None
    tables: list[TableData] = field(default_factory=list)


@dataclass
class PPTData:
    filename: str
    file_hash: str
    slide_count: int
    slides: list[SlideData] = field(default_factory=list)
    slide_width_in: float = 10.0
    slide_height_in: float = 5.625
    aspect_ratio: float = 1.778
    is_16_9: bool = True

    def slim_slides(self, tier: str = "bullets") -> list[dict]:
        """Return minimal slide dicts for LLM context.

        tier="titles_only"  → slide + title only           (~5 tokens/slide)
        tier="bullets"      → slide + title + bullets      (~30 tokens/slide)  DEFAULT
        tier="full_text"    → slide + title + body_text    (~80 tokens/slide)
        """
        if tier == "titles_only":
            return [{"slide": s.number, "title": s.title} for s in self.slides]
        if tier == "full_text":
            return [{"slide": s.number, "title": s.title, "text": s.body_text[:600]}
                    for s in self.slides]
        # default: bullets
        return [{"slide": s.number, "title": s.title, "bullets": s.bullets[:8]}
                for s in self.slides]


class PPTService:

    def extract(self, file_path: str | Path) -> PPTData:
        path = Path(file_path)
        raw = path.read_bytes()
        file_hash = hashlib.sha256(raw).hexdigest()
        prs = Presentation(path)

        slides = []
        for i, slide in enumerate(prs.slides, start=1):
            slides.append(self._extract_slide(i, slide))

        w_in = round(prs.slide_width.inches, 2) if hasattr(prs.slide_width, "inches") else 10.0
        h_in = round(prs.slide_height.inches, 2) if hasattr(prs.slide_height, "inches") else 5.625
        ratio = round(w_in / h_in, 3) if h_in > 0 else 1.778
        is_16_9 = (1.65 <= ratio <= 1.85)

        return PPTData(
            filename=path.name,
            file_hash=file_hash,
            slide_count=len(slides),
            slides=slides,
            slide_width_in=w_in,
            slide_height_in=h_in,
            aspect_ratio=ratio,
            is_16_9=is_16_9,
        )

    def _extract_slide(self, number: int, slide) -> SlideData:
        bullets: list[str] = []
        body_parts: list[str] = []
        fonts: set[str] = set()

        # Extract title via dedicated title shape (index 0 placeholder)
        title_shape = slide.shapes.title
        title = title_shape.text.strip() if title_shape and title_shape.has_text_frame else ""
        title_top = round(title_shape.top.pt, 2) if (title_shape and getattr(title_shape, "top", None) is not None) else None
        title_id = id(title_shape) if (title_shape and title) else None

        # Fallback: if slide.shapes.title is missing or empty, find top-most prominent text shape
        if not title:
            best_shape = None
            best_top = 9999.0
            best_font_size = 0.0
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                txt = shape.text_frame.text.strip()
                if not txt:
                    continue
                # Ignore small footer / slide number shapes
                if len(txt) <= 8 and (txt.isdigit() or txt.lower().startswith(('slide', 'page'))):
                    continue

                s_top = round(shape.top.pt, 2) if getattr(shape, "top", None) is not None else None
                if s_top is not None and s_top < 240.0:
                    p0 = shape.text_frame.paragraphs[0] if shape.text_frame.paragraphs else None
                    f_size = p0.runs[0].font.size.pt if (p0 and p0.runs and p0.runs[0].font.size) else 0.0
                    # Prefer larger font size, or higher top position
                    if f_size > best_font_size or (abs(f_size - best_font_size) < 0.1 and s_top < best_top):
                        best_shape = shape
                        best_top = s_top
                        best_font_size = f_size

            if best_shape:
                title = best_shape.text_frame.text.strip()
                title_top = best_top
                title_id = id(best_shape)

        eyebrow_text: str | None = None
        eyebrow_top: float | None = None

        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            txt = shape.text_frame.text.strip()
            if not txt:
                continue

            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.font.name:
                        fonts.add(run.font.name)

            if id(shape) != title_id:
                bullets.append(txt)
                body_parts.append(txt)

                # Eyebrow check: must sit strictly ABOVE title_top, near top of slide, and be concise
                s_top = round(shape.top.pt, 2) if getattr(shape, "top", None) is not None else None
                if eyebrow_text is None and s_top is not None and title_top is not None:
                    if s_top < title_top - 4.0 and s_top < 180.0 and len(txt.split()) <= 6 and len(txt) <= 60:
                        eyebrow_text = txt
                        eyebrow_top = s_top

        body_text = " ".join(body_parts)
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()

        layout_name = slide.slide_layout.name if slide.slide_layout else ""
        bg_color = self._bg_color(slide)

        shapes_to_check = list(slide.shapes)
        if slide.slide_layout:
            shapes_to_check.extend(list(slide.slide_layout.shapes))
            if slide.slide_layout.slide_master:
                shapes_to_check.extend(list(slide.slide_layout.slide_master.shapes))

        image_positions: list[dict] = self._extract_images_from_shapes(shapes_to_check)
        has_image = len(image_positions) > 0
        content_hash = hashlib.sha256(body_text.encode()).hexdigest()

        pag_info = self._extract_pagination(slide, number)
        tables = self._extract_tables(slide)

        return SlideData(
            number=number,
            title=title,
            bullets=bullets,
            body_text=body_text,
            speaker_notes=notes,
            has_image=has_image,
            layout_name=layout_name,
            font_families=sorted(fonts),
            background_color=bg_color,
            placeholder_count=len(slide.placeholders),
            word_count=len(body_text.split()),
            content_hash=content_hash,
            has_pagination=pag_info["has_pagination"],
            pagination_position=pag_info["position"],
            pagination_font=pag_info["font"],
            pagination_font_size=pag_info["size"],
            pagination_color=pag_info["color"],
            pagination_align=pag_info["align"],
            image_positions=image_positions,
            eyebrow_text=eyebrow_text,
            eyebrow_top=eyebrow_top,
            title_top=title_top,
            tables=tables,
        )

    def _extract_images_from_shapes(self, shapes) -> list[dict]:
        images = []
        for s in shapes:
            stype = getattr(s, "shape_type", None)
            # If shape is a group shape (type 6), recurse into group
            if stype == 6 and hasattr(s, "shapes"):
                images.extend(self._extract_images_from_shapes(s.shapes))
            elif stype == 13 or "pic" in getattr(s, "element", s).tag.lower() or "blip" in getattr(s, "element", s).xml.lower():
                images.append({
                    "left": round(s.left.pt, 2) if getattr(s, "left", None) else 0.0,
                    "top": round(s.top.pt, 2) if getattr(s, "top", None) else 0.0,
                    "width": round(s.width.pt, 2) if getattr(s, "width", None) else 0.0,
                    "height": round(s.height.pt, 2) if getattr(s, "height", None) else 0.0,
                })
        return images

    def _extract_pagination(self, slide, slide_number: int) -> dict:
        import math
        target_left = 21.96
        target_top = 376.00

        shapes_to_check = [("slide", s) for s in slide.shapes]
        if slide.slide_layout:
            shapes_to_check.extend([("layout", s) for s in slide.slide_layout.shapes])
            if slide.slide_layout.slide_master:
                shapes_to_check.extend([("master", s) for s in slide.slide_layout.slide_master.shapes])

        candidates = []
        for layer, shape in shapes_to_check:
            is_num = False
            if shape.is_placeholder and getattr(shape.placeholder_format, "type", None) == 13:
                is_num = True
            elif shape.has_text_frame and ("sldNum" in shape.element.xml or "type=\"slidenum\"" in shape.element.xml):
                is_num = True
            elif shape.has_text_frame and shape.top and shape.top.pt > 300:
                txt = shape.text_frame.text.strip()
                if txt in (str(slide_number), f"Page {slide_number}", f"Slide {slide_number}"):
                    is_num = True

            if is_num:
                l = round(shape.left.pt, 2) if shape.left else 0.0
                t = round(shape.top.pt, 2) if shape.top else 0.0
                w = round(shape.width.pt, 2) if shape.width else 0.0
                h = round(shape.height.pt, 2) if shape.height else 0.0
                dist = math.hypot(l - target_left, t - target_top)

                font_name = None
                font_size = None
                font_color = None
                align = "left"

                if shape.has_text_frame:
                    tf = shape.text_frame
                    for p in tf.paragraphs:
                        if str(p.alignment) in ("LEFT (1)", "PP_ALIGN.LEFT"):
                            align = "left"
                        elif str(p.alignment) in ("RIGHT (3)", "PP_ALIGN.RIGHT"):
                            align = "right"
                        elif str(p.alignment) in ("CENTER (2)", "PP_ALIGN.CENTER"):
                            align = "center"

                        if hasattr(p, "font") and p.font:
                            if p.font.name:
                                font_name = p.font.name
                            if p.font.size:
                                font_size = p.font.size.pt

                        for r in p.runs:
                            if r.font.name:
                                font_name = r.font.name
                            if r.font.size:
                                font_size = r.font.size.pt
                            if r.font.color and r.font.color.type and str(r.font.color.type) != "_NoneColor":
                                try:
                                    font_color = f"#{r.font.color.rgb}"
                                except Exception:
                                    pass

                candidates.append({
                    "has_pagination": True,
                    "position": {"left": l, "top": t, "width": w, "height": h},
                    "font": font_name,
                    "size": font_size,
                    "color": font_color,
                    "align": align,
                    "_dist": dist,
                })

        if not candidates:
            return {
                "has_pagination": False,
                "position": None,
                "font": None,
                "size": None,
                "color": None,
                "align": None,
            }

        best = min(candidates, key=lambda c: c["_dist"])
        if best["_dist"] > 100.0:
            return {
                "has_pagination": False,
                "position": best["position"],
                "font": best["font"],
                "size": best["size"],
                "color": best["color"],
                "align": best["align"],
            }

        return {
            "has_pagination": True,
            "position": best["position"],
            "font": best["font"],
            "size": best["size"],
            "color": best["color"],
            "align": best["align"],
        }

    # ── Table extraction ──────────────────────────────────────────────────────

    def _extract_tables(self, slide) -> list[TableData]:
        """Extract structured metadata from all table shapes on a slide."""
        tables: list[TableData] = []
        for shape in slide.shapes:
            if not getattr(shape, "has_table", False):
                continue
            try:
                tables.append(self._parse_table(shape))
            except Exception:
                pass
        return tables

    def _parse_table(self, shape) -> TableData:
        tbl = shape.table
        rows = tbl.rows
        row_count = len(rows)
        col_count = len(tbl.columns) if tbl.columns else (len(rows[0].cells) if row_count else 0)

        # ── Gather all cells per column ──────────────────────────────────────
        col_cells: list[list] = [[] for _ in range(col_count)]
        for row_idx, row in enumerate(rows):
            for col_idx, cell in enumerate(row.cells):
                if col_idx < col_count:
                    col_cells[col_idx].append((row_idx, cell))

        # ── Header row detection ─────────────────────────────────────────────
        # A header row is the first row when its cells have bold font or
        # background fill that differs from data rows.
        has_header_row = self._detect_header_row(rows)

        # ── Column widths (Rule 3) ────────────────────────────────────────────
        col_widths: list[int] = []
        try:
            col_widths = [c.width for c in tbl.columns]
        except Exception:
            col_widths = []

        # Uniform widths: all widths within 5% of each other
        has_uniform_widths = False
        if len(col_widths) >= 2:
            min_w, max_w = min(col_widths), max(col_widths)
            if min_w > 0:
                has_uniform_widths = (max_w - min_w) / min_w < 0.05

        # ── Cell fill color scan (Rule 10) ────────────────────────────────────
        unique_fill_colors: set[str] = set()
        for row in rows:
            for cell in row.cells:
                color = self._get_cell_fill_color(cell)
                if color and color not in ("#FFFFFF", "#ffffff"):
                    unique_fill_colors.add(color.upper())

        # ── Per-column analysis ──────────────────────────────────────────────
        columns: list[TableColumnData] = []
        all_fonts: list[str] = []
        heavy_border_votes = 0
        total_cells = 0
        dense_cell_count = 0

        for col_idx, cells_in_col in enumerate(col_cells):
            if not cells_in_col:
                continue

            header_text = ""
            header_align = "unknown"
            data_aligns: list[str] = []
            sample_values: list[str] = []
            num_formats: list[str] = []
            col_fonts: list[str] = []

            for row_idx, cell in cells_in_col:
                cell_text = cell.text_frame.text.strip() if cell.text_frame else ""
                is_header = (row_idx == 0 and has_header_row)

                # Alignment
                align = self._get_cell_alignment(cell)

                # Font names
                for para in (cell.text_frame.paragraphs if cell.text_frame else []):
                    for run in para.runs:
                        if run.font.name:
                            col_fonts.append(run.font.name)
                            all_fonts.append(run.font.name)

                # Dense cell check (≥ 3 lines)
                line_count = len([p for p in (cell.text_frame.paragraphs if cell.text_frame else []) if p.text.strip()])
                total_cells += 1
                if line_count >= 3:
                    dense_cell_count += 1

                # Border heaviness check (look at XML lnL/lnR/lnT/lnB)
                if self._has_heavy_border(cell):
                    heavy_border_votes += 1

                if is_header:
                    header_text = cell_text
                    header_align = align
                else:
                    data_aligns.append(align)
                    if cell_text:
                        if len(sample_values) < 5:
                            sample_values.append(cell_text)
                        fmt = self._detect_number_format(cell_text)
                        if fmt:
                            num_formats.append(fmt)

            # Dominant data alignment
            data_alignment = self._dominant(data_aligns) or "unknown"

            # Mixed number formats?
            has_mixed = self._has_mixed_number_format(num_formats)

            # Header vs data alignment mismatch
            hm = (header_align not in ("unknown", data_alignment)) if header_align != "unknown" else False

            # Header verbosity (Rule 8): >4 words in header = too long
            header_wc = len(header_text.split()) if header_text else 0

            # Misalignment detection (Rule 4): numbers should be right, text left, signals center
            columns.append(TableColumnData(
                index=col_idx,
                header_text=header_text,
                data_alignment=data_alignment,
                header_alignment=header_align,
                sample_values=sample_values,
                number_formats=list(set(num_formats)),
                font_names=list(set(col_fonts)),
                width_emu=col_widths[col_idx] if col_idx < len(col_widths) else 0,
                header_word_count=header_wc,
                has_mixed_number_format=has_mixed,
                header_matches_data_align=not hm,
            ))

        # ── Detect heavy borders ─────────────────────────────────────────────
        has_heavy = (heavy_border_votes > 0 and total_cells > 0
                     and heavy_border_votes / total_cells >= 0.7)

        # ── Dense cells ─────────────────────────────────────────────────────
        has_dense = (dense_cell_count > 0 and total_cells > 0
                     and dense_cell_count / total_cells >= 0.4)

        # ── Misaligned columns (Rule 4) ──────────────────────────────────────
        misaligned = self._find_misaligned_columns(columns)

        # ── Verbose headers (Rule 8) — headers > 4 words ─────────────────────
        verbose_header_cols = [c.index for c in columns if c.header_word_count > 4]

        return TableData(
            shape_name=getattr(shape, "name", ""),
            row_count=row_count,
            col_count=col_count,
            has_header_row=has_header_row,
            columns=columns,
            has_heavy_borders=has_heavy,
            has_many_dense_cells=has_dense,
            font_names=list(set(all_fonts)),
            misaligned_columns=misaligned,
            has_uniform_column_widths=has_uniform_widths,
            unique_cell_fill_colors=len(unique_fill_colors),
            verbose_header_columns=verbose_header_cols,
        )

    @staticmethod
    def _get_cell_alignment(cell) -> str:
        """Return 'left', 'right', 'center', 'justify', or 'unknown'."""
        try:
            tf = cell.text_frame
            for para in tf.paragraphs:
                align = para.alignment
                if align is None:
                    continue
                if align == PP_ALIGN.LEFT:
                    return "left"
                if align == PP_ALIGN.RIGHT:
                    return "right"
                if align == PP_ALIGN.CENTER:
                    return "center"
                if align == PP_ALIGN.JUSTIFY:
                    return "justify"
                # fallback: check string representation
                s = str(align).upper()
                if "LEFT" in s:
                    return "left"
                if "RIGHT" in s:
                    return "right"
                if "CENTER" in s:
                    return "center"
        except Exception:
            pass
        return "unknown"

    @staticmethod
    def _has_heavy_border(cell) -> bool:
        """Return True if any border line on the cell has a width > 1pt (heavy)."""
        try:
            xml = cell._tc.xml  # raw XML
            # Look for lnL/lnR/lnT/lnB with w attribute (EMU; 1pt = 12700 EMU)
            widths = re.findall(r'<a:ln[LRTB][^>]*\bw="(\d+)"', xml)
            for w in widths:
                if int(w) > 12700:  # > 1 pt
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _get_cell_fill_color(cell) -> str | None:
        """Return the hex fill color of a table cell, or None if no fill / transparent."""
        try:
            fill = cell.fill
            if fill and fill.type is not None and hasattr(fill, "fore_color"):
                return f"#{fill.fore_color.rgb}"
        except Exception:
            pass
        # Fallback: scan XML for solid fill
        try:
            xml = cell._tc.xml
            # <a:solidFill><a:srgbClr val="EA1B3D"/>
            m = re.search(r'<a:srgbClr\s+val="([0-9A-Fa-f]{6})"', xml)
            if m:
                return f"#{m.group(1).upper()}"
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_number_format(text: str) -> str | None:
        """Classify a cell value into a number-format bucket for consistency checking."""
        t = text.strip()
        if not t:
            return None
        # Currency short: $2.4M / $1.9B / €3.2M
        if re.match(r'^[\$€£][\d,]+(?:\.\d+)?[MBKTmbt]$', t):
            return 'currency_short'
        # Currency long: $1,850,000 or $1850000
        if re.match(r'^[\$€£][\d,]{4,}$', t):
            return 'currency_long'
        # Currency words: $3.1 Million / 1.2 billion
        if re.match(r'^[\$€£]?[\d.]+\s+(million|billion|trillion|thousand)$', t, re.IGNORECASE):
            return 'currency_word'
        # Percent integer: 18% / 5%
        if re.match(r'^\d+%$', t):
            return 'percent_int'
        # Percent float: 18.0% / 5.25%
        if re.match(r'^\d+\.\d+%$', t):
            return 'percent_float'
        # Percent word: 18 percent
        if re.match(r'^\d+(?:\.\d+)?\s+percent$', t, re.IGNORECASE):
            return 'percent_word'
        return None

    @staticmethod
    def _has_mixed_number_format(formats: list[str]) -> bool:
        """True if the same column mixes incompatible number formats."""
        if len(formats) < 2:
            return False
        currency_formats = {f for f in formats if 'currency' in f}
        percent_formats  = {f for f in formats if 'percent' in f}
        # Mixed within currency family
        if len(currency_formats) > 1:
            return True
        # Mixed within percent family
        if len(percent_formats) > 1:
            return True
        return False

    @staticmethod
    def _dominant(values: list[str]) -> str | None:
        """Return the most frequent value in a list."""
        if not values:
            return None
        return max(set(values), key=values.count)

    @staticmethod
    def _detect_header_row(rows) -> bool:
        """Heuristic: first row is a header if its cells are bold or have background fill."""
        try:
            if not rows:
                return False
            first_row = rows[0]
            for cell in first_row.cells:
                if not cell.text_frame:
                    continue
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        if run.font.bold is True:
                            return True
                # Check cell fill (non-transparent fill = header styling)
                try:
                    fill = cell.fill
                    if fill and fill.type is not None:
                        return True
                except Exception:
                    pass
        except Exception:
            pass
        # Fallback: if first row contains short ALL-CAPS or Title Case text, treat as header
        try:
            first_cells_text = [c.text_frame.text.strip() for c in rows[0].cells if c.text_frame]
            if all(t and (t.isupper() or t.istitle() or len(t.split()) <= 4) for t in first_cells_text if t):
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _find_misaligned_columns(columns: list) -> list[int]:
        """
        Rule 4 & 5: Flag columns where alignment contradicts the content type.
        - Numeric columns should be RIGHT aligned
        - Text-heavy columns should be LEFT aligned
        - Signal/short-category columns may be CENTER
        Returns list of 0-based column indices that appear misaligned.
        """
        misaligned: list[int] = []
        # Patterns that indicate numeric content
        NUM_PATTERNS = re.compile(
            r'^[\$€£%\d]|[\$€£%]$|[MBKmbt]$|^\d+$|^\d+[.,]\d+$'
        )
        # Short signal words
        SIGNAL_WORDS = {"yes", "no", "on track", "at risk", "off track", "green", "amber", "red",
                        "done", "pending", "complete", "incomplete", "tbd", "n/a", "✓", "✗", "●", "○"}

        for col in columns:
            if col.data_alignment in ("unknown", None):
                continue  # cannot assess

            # Sample values determine expected alignment
            samples = [v.strip().lower() for v in col.sample_values if v.strip()]
            if not samples:
                continue

            num_samples = sum(1 for s in samples if NUM_PATTERNS.match(s))
            sig_samples = sum(1 for s in samples if s in SIGNAL_WORDS)
            text_samples = len(samples) - num_samples - sig_samples

            dominant_type = "text"
            if num_samples > len(samples) / 2:
                dominant_type = "numeric"
            elif sig_samples > len(samples) / 2:
                dominant_type = "signal"

            expected = {"numeric": "right", "signal": "center", "text": "left"}.get(dominant_type, "left")

            if col.data_alignment != expected and col.data_alignment != "unknown":
                misaligned.append(col.index)

        return misaligned

    def _bg_color(self, slide) -> str | None:
        try:
            bg = slide.background
            fill = bg.fill
            if fill.type is not None and hasattr(fill, "fore_color"):
                rgb = fill.fore_color.rgb
                return f"#{rgb}"
        except Exception:
            pass
        return None

