"""Visual quality agent — hybrid rule-based layout inspection + LLM readability analysis."""
from __future__ import annotations
import json
from agents.base import AgentContract, ReviewAgent, AgentStatus, Finding, Severity, ActionType
from agents.llm_mixin import LLMAgentMixin
from agents.registry import register_agent
from services.normalization_service import NormalizationService
from services.rule_service import RuleService

_rule_svc = RuleService()


class VisualQualityAgent(LLMAgentMixin, ReviewAgent):
    agent_id = "visual_quality"

    def run(self, context: dict) -> AgentContract:
        try:
            ppt = context["ppt_data"]

            # 1. Execute deterministic rule-based visual quality checks
            # Merge visual_quality rules + table_design rules from YAML/DB
            vq_rules = context.get("rules", []) or _rule_svc.get_rules("visual_quality")
            tbl_rules = _rule_svc.get_rules("table_design")
            # Also pull allowed_font rules from branding domain for table font checks
            brand_rules = _rule_svc.get_rules("branding")
            all_rules = vq_rules + tbl_rules + [r for r in brand_rules if r.get("type") == "allowed_font"]
            rule_findings = self._run_rule_checks(ppt, all_rules)

            # 2. Execute qualitative LLM prompt analysis
            prompt = self._get_prompt(context)
            user = self._format_prompt(
                prompt["user_template"],
                slides=json.dumps(ppt.slim_slides("bullets"), ensure_ascii=False),
                slide_count=ppt.slide_count,
            )
            raw = self._llm_call(context, prompt["system"], user, prompt.get("version_id"))

            llm_findings = []
            if raw and isinstance(raw, dict):
                llm_findings = self._parse_findings(raw)

            # 3. Combine & deduplicate findings
            all_findings = rule_findings + llm_findings
            normalizer = NormalizationService(similarity_threshold=0.25)
            consolidated_findings = normalizer.normalize_and_deduplicate(all_findings)

            # 4. Compute visual quality score deterministically
            score = 100
            for f in consolidated_findings:
                if f.severity == Severity.HIGH:
                    score -= 15
                elif f.severity == Severity.MEDIUM:
                    score -= 10
                elif f.severity == Severity.LOW:
                    score -= 5
            score = max(0, min(100, score))

            status = AgentStatus.PASS if score >= 80 else (AgentStatus.PARTIAL if score >= 60 else AgentStatus.FAIL)
            summary = (
                f"Visual quality review completed with {len(rule_findings)} rule-based checks "
                f"and {len(llm_findings)} LLM visual findings."
            )

            return AgentContract(
                agent_id=self.agent_id,
                status=status,
                score=score,
                findings=consolidated_findings,
                summary=summary,
                confidence=0.95,
            )
        except Exception as exc:
            return self._failed(str(exc))

    def _run_rule_checks(self, ppt, rules: list[dict] | None = None) -> list[Finding]:
        findings: list[Finding] = []
        all_fonts: set[str] = set()

        # Dynamic thresholds loaded from rules.yaml / DB
        rules = rules or []
        max_bullets = int(next((r["value"] for r in rules if r.get("type") == "max_bullets_per_slide"), 7))
        max_words = int(next((r["value"] for r in rules if r.get("type") == "max_words_per_slide"), 150))
        min_words = int(next((r["value"] for r in rules if r.get("type") == "min_words_per_slide"), 10))
        max_fonts = int(next((r["value"] for r in rules if r.get("type") == "max_font_families_per_deck"), 3))

        for slide in ppt.slides:
            # Accumulate fonts across deck
            if slide.font_families:
                all_fonts.update(slide.font_families)

            # Rule 1: Bullet count overload (> max_bullets)
            bullet_count = len(slide.bullets)
            if bullet_count > max_bullets:
                findings.append(Finding(
                    id=f"VIS-RULE-001-S{slide.number}",
                    slide=slide.number,
                    severity=Severity.MEDIUM,
                    category="visual_density",
                    title="Bullet point overload",
                    description=f"Slide {slide.number} contains {bullet_count} bullet points causing dense text clutter.",
                    recommendation="Limit slide bullets to 4-5 key takeaways or split details across slides.",
                    confidence=1.0,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} has {bullet_count} bullets.",
                    rule_id="VIS-RULE-001",
                ))

            # Rule 2: Text word count density (> max_words)
            if slide.word_count > max_words:
                findings.append(Finding(
                    id=f"VIS-RULE-002-S{slide.number}",
                    slide=slide.number,
                    severity=Severity.MEDIUM,
                    category="text_density",
                    title="High layout text density",
                    description=f"Slide {slide.number} contains {slide.word_count} words, exceeding comfortable visual reading density.",
                    recommendation="Trim text volume or convert text paragraphs into visual callouts or diagrams.",
                    confidence=1.0,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} word count: {slide.word_count} words.",
                    rule_id="VIS-RULE-002",
                ))

            # Rule 3: Sparse / Low Content Slide (< min_words, no image, non-title slide)
            if slide.number > 1 and slide.word_count < min_words and not slide.has_image:
                findings.append(Finding(
                    id=f"VIS-RULE-003-S{slide.number}",
                    slide=slide.number,
                    severity=Severity.LOW,
                    category="slide_completeness",
                    title="Low slide content density",
                    description=f"Slide {slide.number} contains only {slide.word_count} words and no visual graphics.",
                    recommendation="Ensure slide communicates a clear takeaway or remove redundant slide.",
                    confidence=1.0,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} word count: {slide.word_count}, images: 0.",
                    rule_id="VIS-RULE-003",
                ))

            # Rule 4: Missing Slide Title
            if not slide.title or len(slide.title.strip()) == 0:
                findings.append(Finding(
                    id=f"VIS-RULE-004-S{slide.number}",
                    slide=slide.number,
                    severity=Severity.MEDIUM,
                    category="slide_structure",
                    title="Missing slide title",
                    description=f"Slide {slide.number} lacks a main title header.",
                    recommendation="Add a clear headline/title to establish slide context.",
                    confidence=1.0,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} title field is empty.",
                    rule_id="VIS-RULE-004",
                ))

            # Table Design Rules
            table_findings = self._run_table_checks(slide, rules)
            findings.extend(table_findings)

        # Rule 5: Deck-level Font Family Variety (> max_fonts)
        if len(all_fonts) > max_fonts:
            fonts_str = ", ".join(sorted(all_fonts))
            findings.append(Finding(
                id="VIS-RULE-005-DECK",
                slide=0,
                severity=Severity.MEDIUM,
                category="typography_consistency",
                title="Excessive font family variety",
                description=f"Presentation uses {len(all_fonts)} distinct font families ({fonts_str}).",
                recommendation=f"Limit presentation to 2-{max_fonts} standard brand font families for typographic consistency.",
                confidence=1.0,
                action_type=ActionType.RECOMMENDATION_ONLY,
                evidence=f"Font families detected across deck: {fonts_str}.",
                rule_id="VIS-RULE-005",
            ))

        return findings

    def _run_table_checks(self, slide, rules: list[dict]) -> list[Finding]:
        """Run all Table Design Guideline checks for tables on a slide."""
        findings: list[Finding] = []
        tables = getattr(slide, "tables", [])
        if not tables:
            return findings

        # Load table thresholds from rules
        max_cols_ideal = int(next((r["value"] for r in rules if r.get("type") == "tbl_max_columns_ideal"), 6))
        max_cols_acceptable = int(next((r["value"] for r in rules if r.get("type") == "tbl_max_columns_acceptable"), 8))
        check_alignment = str(next((r["value"] for r in rules if r.get("type") == "tbl_check_column_alignment"), "true")).lower() == "true"
        check_borders = str(next((r["value"] for r in rules if r.get("type") == "tbl_check_border_minimalism"), "true")).lower() == "true"
        check_fonts = str(next((r["value"] for r in rules if r.get("type") == "tbl_check_font_consistency"), "true")).lower() == "true"
        check_numbers = str(next((r["value"] for r in rules if r.get("type") == "tbl_check_number_format_consistency"), "true")).lower() == "true"
        require_header = str(next((r["value"] for r in rules if r.get("type") == "tbl_require_header_row"), "true")).lower() == "true"

        # Collect deck brand fonts for font consistency check
        allowed_brand_fonts_lc = {"lexend"}  # default; expand from rules if available
        allowed_fonts_rules = [r["value"].lower() for r in rules if r.get("type") == "allowed_font"]
        if allowed_fonts_rules:
            allowed_brand_fonts_lc = {f.lower() for f in allowed_fonts_rules}

        for tbl_idx, tbl in enumerate(tables, start=1):
            tbl_label = f"Table {tbl_idx}" if len(tables) > 1 else "Table"
            col_count = tbl.col_count

            # ── TBL-RULE-001: Column count advisory (7–8 columns) ──────────────
            if max_cols_ideal < col_count <= max_cols_acceptable:
                findings.append(Finding(
                    id=f"TBL-RULE-001-S{slide.number}-T{tbl_idx}",
                    slide=slide.number,
                    severity=Severity.LOW,
                    category="table_design",
                    title=f"Table column count approaching limit ({col_count} columns)",
                    description=(
                        f"Slide {slide.number} {tbl_label} has {col_count} columns. "
                        f"Executive tables should ideally have 4–{max_cols_ideal} columns. "
                        f"7–{max_cols_acceptable} columns are acceptable but require careful design."
                    ),
                    recommendation=(
                        "Consider whether all columns are essential. Remove information that doesn't support "
                        "the key message, or combine related columns to improve scannability."
                    ),
                    confidence=1.0,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} {tbl_label}: {col_count} columns detected.",
                    rule_id="TBL-RULE-001",
                ))

            # ── TBL-RULE-002: Column count critical (9+ columns) ──────────────
            elif col_count > max_cols_acceptable:
                findings.append(Finding(
                    id=f"TBL-RULE-002-S{slide.number}-T{tbl_idx}",
                    slide=slide.number,
                    severity=Severity.HIGH,
                    category="table_design",
                    title=f"Table has too many columns ({col_count}) — reconsider structure",
                    description=(
                        f"Slide {slide.number} {tbl_label} has {col_count} columns. "
                        f"Tables with 9+ columns turn an executive slide into an Excel worksheet "
                        f"and are impossible to scan quickly."
                    ),
                    recommendation=(
                        "Split the table into multiple focused tables, move detail to an appendix, "
                        "or replace with a chart that shows the same insight visually. "
                        "Ideally limit executive tables to 4–6 columns."
                    ),
                    confidence=1.0,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} {tbl_label}: {col_count} columns detected (limit: {max_cols_acceptable}).",
                    rule_id="TBL-RULE-002",
                ))

            # ── TBL-RULE-003: Missing header row ──────────────────────────────
            if require_header and not tbl.has_header_row:
                findings.append(Finding(
                    id=f"TBL-RULE-003-S{slide.number}-T{tbl_idx}",
                    slide=slide.number,
                    severity=Severity.MEDIUM,
                    category="table_design",
                    title="Table missing a visually distinct header row",
                    description=(
                        f"Slide {slide.number} {tbl_label} does not appear to have a clearly styled header row. "
                        f"Headers should be bold, filled, or visually distinct from body rows to anchor the table."
                    ),
                    recommendation=(
                        "Apply bold formatting or a subtle background fill to the first row. "
                        "Keep headers short, clear, and consistent — they should communicate column meaning "
                        "without becoming a sentence."
                    ),
                    confidence=0.85,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} {tbl_label}: no bold or filled header cells detected in row 1.",
                    rule_id="TBL-RULE-003",
                ))

            # ── TBL-RULE-004: Column alignment — wrong content-type alignment ─
            if check_alignment and tbl.misaligned_columns:
                col_labels = []
                for ci in tbl.misaligned_columns:
                    col = next((c for c in tbl.columns if c.index == ci), None)
                    if col:
                        hdr = col.header_text or f"Column {ci + 1}"
                        col_labels.append(
                            f"'{hdr}' (detected as {col.data_alignment}, "
                            f"expected {'right for numbers' if any(f in ('currency_short','currency_long','percent_int','percent_float') for f in col.number_formats) else 'left for text'})"
                        )
                if col_labels:
                    findings.append(Finding(
                        id=f"TBL-RULE-004-S{slide.number}-T{tbl_idx}",
                        slide=slide.number,
                        severity=Severity.MEDIUM,
                        category="table_design",
                        title="Table column alignment does not match content type",
                        description=(
                            f"Slide {slide.number} {tbl_label} has columns where alignment contradicts "
                            f"content type: {', '.join(col_labels)}."
                        ),
                        recommendation=(
                            "Apply alignment by content type: "
                            "Text (names, descriptions, initiatives) → Left | "
                            "Numbers (revenue, cost, %, counts) → Right | "
                            "Signals (status, Yes/No, icons, ratings) → Center. "
                            "Headers should generally follow the same alignment as the data below them."
                        ),
                        confidence=0.80,
                        action_type=ActionType.RECOMMENDATION_ONLY,
                        evidence=f"Slide {slide.number} {tbl_label}: misaligned column indices (0-based): {tbl.misaligned_columns}.",
                        rule_id="TBL-RULE-004",
                    ))

            # ── TBL-RULE-005: Header alignment doesn't match data alignment ──
            if check_alignment:
                mismatched_headers = [
                    c for c in tbl.columns
                    if not c.header_matches_data_align
                    and c.header_alignment != "unknown"
                    and c.data_alignment != "unknown"
                ]
                if mismatched_headers:
                    hdr_details = ", ".join(
                        f"'{c.header_text or f'Col {c.index+1}'}' (header: {c.header_alignment}, data: {c.data_alignment})"
                        for c in mismatched_headers
                    )
                    findings.append(Finding(
                        id=f"TBL-RULE-005-S{slide.number}-T{tbl_idx}",
                        slide=slide.number,
                        severity=Severity.LOW,
                        category="table_design",
                        title="Table header alignment differs from column data alignment",
                        description=(
                            f"Slide {slide.number} {tbl_label} has headers misaligned with their data: {hdr_details}."
                        ),
                        recommendation=(
                            "As a default, the header should follow the alignment of the values underneath it. "
                            "For example, a Revenue column header should be right-aligned like the values. "
                            "Exception: a very long numeric header may be left-aligned if it creates a cleaner result."
                        ),
                        confidence=0.75,
                        action_type=ActionType.RECOMMENDATION_ONLY,
                        evidence=f"Slide {slide.number} {tbl_label}: header-to-data alignment mismatches found.",
                        rule_id="TBL-RULE-005",
                    ))

            # ── TBL-RULE-006: Number format inconsistency in columns ──────────
            if check_numbers:
                mixed_cols = [c for c in tbl.columns if c.has_mixed_number_format]
                for col in mixed_cols:
                    hdr = col.header_text or f"Column {col.index + 1}"
                    findings.append(Finding(
                        id=f"TBL-RULE-006-S{slide.number}-T{tbl_idx}-C{col.index}",
                        slide=slide.number,
                        severity=Severity.MEDIUM,
                        category="table_design",
                        title=f"Inconsistent number format in '{hdr}' column",
                        description=(
                            f"Slide {slide.number} {tbl_label} column '{hdr}' mixes incompatible number formats "
                            f"(detected: {', '.join(col.number_formats)}). "
                            f"Example: mixing '$2.4M' with '$1,850,000' or '18%' with '18.0%' makes the table "
                            f"harder to scan and compare."
                        ),
                        recommendation=(
                            "Standardize number formats within a column: pick one convention and apply it consistently. "
                            "Use the level of precision that supports the decision — "
                            "if the difference between 18.1% and 18.14% doesn't affect the decision, show 18%."
                        ),
                        confidence=0.85,
                        action_type=ActionType.RECOMMENDATION_ONLY,
                        evidence=f"Slide {slide.number} {tbl_label} column '{hdr}': formats detected: {col.number_formats}.",
                        rule_id="TBL-RULE-006",
                    ))

            # ── TBL-RULE-007: Heavy borders (spreadsheet-style) ───────────────
            if check_borders and tbl.has_heavy_borders:
                findings.append(Finding(
                    id=f"TBL-RULE-007-S{slide.number}-T{tbl_idx}",
                    slide=slide.number,
                    severity=Severity.LOW,
                    category="table_design",
                    title="Table uses heavy borders on all cells (spreadsheet style)",
                    description=(
                        f"Slide {slide.number} {tbl_label} has uniform heavy borders around every cell, "
                        f"which gives it a spreadsheet appearance rather than an executive table feel."
                    ),
                    recommendation=(
                        "Reduce border weight. Prefer a clear header separator with subtle horizontal "
                        "lines between rows. Use white space to create separation and grouping. "
                        "Goal: the table should feel like part of the presentation — not an exported spreadsheet."
                    ),
                    confidence=0.80,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} {tbl_label}: heavy cell borders detected on ≥70% of cells.",
                    rule_id="TBL-RULE-007",
                ))

            # ── TBL-RULE-008: Dense multi-line cells ─────────────────────────
            if tbl.has_many_dense_cells:
                findings.append(Finding(
                    id=f"TBL-RULE-008-S{slide.number}-T{tbl_idx}",
                    slide=slide.number,
                    severity=Severity.MEDIUM,
                    category="table_design",
                    title="Table has too many cells with dense multi-line content",
                    description=(
                        f"Slide {slide.number} {tbl_label} has many cells containing 3 or more lines of text. "
                        f"The 5-second scan test fails: an executive cannot quickly extract the key information."
                    ),
                    recommendation=(
                        "Keep text concise. Avoid having every cell contain 3–4 lines of text. "
                        "Ask: can I scan five rows quickly without feeling that I am reading a document? "
                        "If not, simplify the table, reduce content, or move detail to an appendix."
                    ),
                    confidence=0.80,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} {tbl_label}: ≥40% of cells have 3+ lines of content.",
                    rule_id="TBL-RULE-008",
                ))

            # ── TBL-RULE-009: Non-brand font in table ────────────────────────
            if check_fonts and tbl.font_names:
                non_brand_fonts = [
                    f for f in tbl.font_names
                    if not any(f.lower() == bf or f.lower().startswith(bf + " ") for bf in allowed_brand_fonts_lc)
                ]
                if non_brand_fonts:
                    findings.append(Finding(
                        id=f"TBL-RULE-009-S{slide.number}-T{tbl_idx}",
                        slide=slide.number,
                        severity=Severity.LOW,
                        category="table_design",
                        title=f"Table uses non-brand font: {', '.join(non_brand_fonts)}",
                        description=(
                            f"Slide {slide.number} {tbl_label} uses font(s) '{', '.join(non_brand_fonts)}' "
                            f"which differ from the brand font family. "
                            f"Tables should use the same font family as the rest of the presentation."
                        ),
                        recommendation=(
                            "Apply the brand font (Lexend) to all table cells. "
                            "Make headers slightly bolder than body text. "
                            "Maintain sufficient font size for screen viewing — "
                            "do not shrink the font to accommodate more content. "
                            "If the table doesn't fit, fix the table — not the font size."
                        ),
                        confidence=0.90,
                        action_type=ActionType.RECOMMENDATION_ONLY,
                        evidence=f"Slide {slide.number} {tbl_label}: fonts detected: {tbl.font_names}.",
                        rule_id="TBL-RULE-009",
                    ))

            # ── TBL-RULE-010: Uniform column widths (Rule 3 — density ignored) ─
            if tbl.has_uniform_column_widths and col_count >= 3:
                findings.append(Finding(
                    id=f"TBL-RULE-010-S{slide.number}-T{tbl_idx}",
                    slide=slide.number,
                    severity=Severity.LOW,
                    category="table_design",
                    title="Table columns have identical widths — information density ignored",
                    description=(
                        f"Slide {slide.number} {tbl_label} has {col_count} columns with equal widths. "
                        f"Executive table guidelines recommend allocating column width based on "
                        f"information density, not geometric symmetry."
                    ),
                    recommendation=(
                        "Give more width to text-heavy columns (e.g. Initiative, Description, Recommendation) "
                        "and less width to short fields (e.g. Status, Year, Count, Rating). "
                        "Column width should follow the amount of information the audience needs to read."
                    ),
                    confidence=0.70,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} {tbl_label}: all {col_count} columns detected with equal widths.",
                    rule_id="TBL-RULE-010",
                ))

            # ── TBL-RULE-011: Verbose header text (Rule 8 — header as anchor) ─
            if tbl.verbose_header_columns:
                verbose_details = []
                for ci in tbl.verbose_header_columns:
                    col = next((c for c in tbl.columns if c.index == ci), None)
                    if col and col.header_text:
                        verbose_details.append(f"'{col.header_text}' ({col.header_word_count} words)")
                if verbose_details:
                    findings.append(Finding(
                        id=f"TBL-RULE-011-S{slide.number}-T{tbl_idx}",
                        slide=slide.number,
                        severity=Severity.LOW,
                        category="table_design",
                        title="Table has verbose column headers that are too long",
                        description=(
                            f"Slide {slide.number} {tbl_label} has column headers that read like sentences "
                            f"rather than short labels: {', '.join(verbose_details)}. "
                            f"Long headers reduce scannability and visual hierarchy."
                        ),
                        recommendation=(
                            "Shorten column headers to 1–4 words. "
                            "Prefer 'Revenue Potential' over 'Estimated Annualized Revenue Potential'. "
                            "Prefer 'Status' over 'Current Project Delivery Status'. "
                            "The header should communicate column meaning — not become a sentence."
                        ),
                        confidence=0.85,
                        action_type=ActionType.RECOMMENDATION_ONLY,
                        evidence=f"Slide {slide.number} {tbl_label}: verbose headers at column indices {tbl.verbose_header_columns}.",
                        rule_id="TBL-RULE-011",
                    ))

            # ── TBL-RULE-012: Excessive decorative cell shading (Rule 10) ──────
            if tbl.unique_cell_fill_colors >= 4:
                findings.append(Finding(
                    id=f"TBL-RULE-012-S{slide.number}-T{tbl_idx}",
                    slide=slide.number,
                    severity=Severity.MEDIUM,
                    category="table_design",
                    title=f"Table uses too many cell fill colors ({tbl.unique_cell_fill_colors} colors) — decorative overuse",
                    description=(
                        f"Slide {slide.number} {tbl_label} has {tbl.unique_cell_fill_colors} distinct cell "
                        f"background colors. Using a different color for every column (or excessive shading) "
                        f"treats color as decoration rather than communication."
                    ),
                    recommendation=(
                        "Use color with a specific purpose: "
                        "Green → On Track | Amber → At Risk | Red → Off Track | "
                        "Blue → Selected/highlighted | Grey → Secondary information. "
                        "Avoid giving every column a different color or applying excessive cell shading. "
                        "Highlight only the information you want the executive to notice first."
                    ),
                    confidence=0.75,
                    action_type=ActionType.RECOMMENDATION_ONLY,
                    evidence=f"Slide {slide.number} {tbl_label}: {tbl.unique_cell_fill_colors} distinct non-white cell fill colors detected.",
                    rule_id="TBL-RULE-012",
                ))

        return findings


register_agent("visual_quality", VisualQualityAgent, stage="content_extraction", execution_mode="parallel")
