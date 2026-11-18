"""PDF report generator — renders a Jinja2 HTML template and converts to PDF via WeasyPrint.

Responsibilities of this module (Python only — no HTML/CSS strings):
  - Load and cache the Jinja2 template and CSS stylesheet from templates/report/
  - Transform raw run_data into clean, template-ready context objects
  - Provide build_html() and generate_pdf() as the public API

Templates:
  templates/report/report.html.j2  — full HTML layout (Jinja2)
  templates/report/report.css      — all CSS styles
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ── Template loader setup ──────────────────────────────────────────────────────
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_REPORT_CSS    = (_TEMPLATES_DIR / "report" / "report.css").read_text(encoding="utf-8")

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "j2"]),
    auto_reload=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

# ── Agent display metadata ─────────────────────────────────────────────────────
_AGENT_META: dict[str, dict[str, str]] = {
    "branding":         {"name": "Branding",         "type": "rule"},
    "template":         {"name": "Template",         "type": "rule"},
    "visual_quality":   {"name": "Visual Quality",   "type": "rule"},
    "content":          {"name": "Content Quality",  "type": "llm"},
    "story":            {"name": "Story Arc",         "type": "llm"},
    "customer_focus":   {"name": "Customer Focus",   "type": "llm"},
    "proposal_context": {"name": "Proposal Context", "type": "llm"},
    "cio_lens":         {"name": "CIO Lens",         "type": "llm"},
    "critic":           {"name": "Critic",           "type": "llm"},
}

_ACTION_TYPE_LABELS: dict[str, str] = {
    "AUTO_FIX":            "Auto-fix",
    "AUTO_FIXABLE":        "Auto-fix",
    "HUMAN_APPROVAL":      "Approval",
    "RECOMMENDATION_ONLY": "Recommend",
}

_SEVERITY_ORDER: dict[str, int] = {
    "CRITICAL": 0,
    "HIGH":     1,
    "MEDIUM":   2,
    "LOW":      3,
}


# ── Pure helper functions ──────────────────────────────────────────────────────

def friendly_name(agent_id: str) -> str:
    """Return a human-readable display name for an agent ID.

    Looks up _AGENT_META first; falls back to converting snake_case → Title Case
    so any future agent IDs are never shown raw (e.g. 'visual_quality' → 'Visual Quality').
    """
    if agent_id in _AGENT_META:
        return _AGENT_META[agent_id]["name"]
    return " ".join(word.capitalize() for word in agent_id.split("_"))


def score_class(score: int) -> str:
    """Map a numeric score to a CSS class name: pass / warn / fail."""
    if score >= 80:
        return "pass"
    if score >= 60:
        return "warn"
    return "fail"


def score_label(score: int) -> str:
    """Map a numeric score to a human-readable readiness label."""
    if score >= 80:
        return "READY"
    if score >= 60:
        return "REVIEW"
    return "BLOCKED"


def format_summary_html(summary: object) -> str:
    """Convert a plain-text summary string into an HTML bullet list if it spans
    multiple sentences/lines, or a plain span for single-line summaries."""
    if not summary or str(summary).strip() in ("", "—"):
        return "—"
    raw = str(summary).strip()
    lines = [ln.strip().lstrip("•-*\t ").strip() for ln in raw.splitlines() if ln.strip()]
    if len(lines) <= 1:
        sentences = [s.strip() for s in re.split(r'(?<=\.)\s+(?=[A-Z0-9])', raw) if s.strip()]
        if len(sentences) > 1:
            lines = sentences
    if len(lines) > 1:
        items = "".join(
            f"<li style='margin-bottom:4px;'>{_esc(line)}</li>"
            for line in lines
        )
        return (
            "<ul style='margin:0;padding-left:14px;list-style-type:disc;"
            "font-size:8pt;color:#373742;text-align:left;line-height:1.4;'>"
            f"{items}</ul>"
        )
    return f"<span style='font-size:8pt;color:#373742;text-align:left;'>{_esc(raw)}</span>"


def _esc(value: object) -> str:
    """HTML-escape a value. Used internally when building non-autoescape strings."""
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _slide_sort_key(finding: dict) -> int:
    """Return a sort key for a finding's slide number (deck-level → very high)."""
    try:
        return int(finding.get("slide") or 0) or 10_000
    except (TypeError, ValueError):
        return 10_000


# ── Context builders ───────────────────────────────────────────────────────────

def _build_pills(all_findings: list[dict], completed: list, failed: list) -> list[dict]:
    """Build the status pill list for the report header."""
    pills = []
    critical_n = sum(1 for f in all_findings if f.get("severity") == "CRITICAL")
    high_n     = sum(1 for f in all_findings if f.get("severity") == "HIGH")
    if critical_n:
        pills.append({"cls": "fail", "icon": "🔴", "label": f"{critical_n} Critical"})
    if high_n:
        pills.append({"cls": "fail", "icon": "🟠", "label": f"{high_n} High"})
    if completed:
        pills.append({"cls": "ok", "icon": "✓", "label": f"{len(completed)} Agents Passed"})
    if failed:
        s = "s" if len(failed) > 1 else ""
        pills.append({"cls": "warn", "icon": "⚠", "label": f"{len(failed)} Agent{s} Failed"})
    if not all_findings:
        pills.append({"cls": "ok", "icon": "✓", "label": "No findings"})
    return pills


def _build_agent_rows(agent_results: list[dict]) -> list[dict]:
    """Transform raw agent result dicts into template-ready row dicts."""
    rows = []
    for agent in agent_results:
        aid = agent.get("agent_id", "")
        meta = _AGENT_META.get(aid, {"name": friendly_name(aid), "type": "llm"})
        sc   = agent.get("score") or 0
        rows.append({
            "display_name":   meta["name"],
            "type":           meta["type"],
            "status":         agent.get("status", "unknown"),
            "score":          sc,
            "score_class":    score_class(sc),
            "findings_count": len(agent.get("findings") or []),
            "summary_html":   format_summary_html(agent.get("summary", "")),
        })
    return rows


def _build_finding_groups(all_findings: list[dict]) -> list[tuple[str, list[dict]]]:
    """Sort findings by slide then severity, group by slide label, and enrich
    each finding dict with template-ready display fields."""
    sorted_findings = sorted(
        all_findings,
        key=lambda f: (_slide_sort_key(f), _SEVERITY_ORDER.get(f.get("severity", "LOW"), 4)),
    )

    groups: list[tuple[str, list[dict]]] = []
    current_key: str | None = None
    current_group: list[dict] = []

    for raw_f in sorted_findings:
        slide_val = raw_f.get("slide")
        key = f"Slide {slide_val}" if slide_val else "Deck Level"

        if key != current_key:
            if current_group:
                groups.append((current_key, current_group))
            current_key   = key
            current_group = []

        action_type = raw_f.get("action_type", "RECOMMENDATION_ONLY")
        rec_txt     = str(raw_f.get("recommendation", "") or "").strip()

        current_group.append({
            **raw_f,
            "agent_name":          friendly_name(raw_f.get("agent", "")),
            "action_type_short":   _ACTION_TYPE_LABELS.get(action_type, action_type),
            "recommendation_html": format_summary_html(rec_txt) if rec_txt else "",
        })

    if current_group:
        groups.append((current_key, current_group))

    return groups


# ── Public API ─────────────────────────────────────────────────────────────────

def build_html(run_data: dict) -> str:
    """Render the Jinja2 report template with enriched context derived from run_data.

    Args:
        run_data: The full review run result dictionary as stored/returned by ReviewService.

    Returns:
        A complete HTML string ready for WeasyPrint or browser viewing.
    """
    overall_score = run_data.get("score") or 0
    filename      = run_data.get("filename", run_data.get("run_id", "unknown"))
    agent_results = run_data.get("agent_results", [])
    run_id        = run_data.get("run_id", "")
    started_at    = run_data.get("started_at", "")
    cost          = run_data.get("cost", {})

    # Flatten all findings and tag each with its agent ID
    all_findings: list[dict] = []
    for agent in agent_results:
        for finding in (agent.get("findings") or []):
            all_findings.append({**finding, "agent": agent.get("agent_id", "")})

    completed = [a for a in agent_results if a.get("status") == "completed"]
    failed    = [a for a in agent_results if a.get("status") == "failed"]

    # Format timestamps
    try:
        started_fmt = (
            datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
            .strftime("%d %b %Y %H:%M UTC")
        )
    except Exception:
        started_fmt = str(started_at)

    generated_at = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

    context = {
        # Scores & status
        "score":       overall_score,
        "score_class": score_class(overall_score),
        "score_label": score_label(overall_score),

        # Metadata
        "filename":      filename,
        "run_id":        run_id,
        "started_fmt":   started_fmt,
        "generated_at":  generated_at,

        # Cost
        "total_tokens": int((cost.get("input_tokens") or 0) + (cost.get("output_tokens") or 0)),
        "cost_usd":     float(cost.get("cost_usd") or 0),

        # Counts for score banner
        "critical_n":  sum(1 for f in all_findings if f.get("severity") == "CRITICAL"),
        "high_n":      sum(1 for f in all_findings if f.get("severity") == "HIGH"),
        "completed_n": len(completed),
        "failed_n":    len(failed),

        # Template-ready data structures
        "all_findings":   all_findings,
        "agent_results":  _build_agent_rows(agent_results),
        "finding_groups": _build_finding_groups(all_findings),
        "pills":          _build_pills(all_findings, completed, failed),

        # Inlined CSS (avoids external file resolution issues in WeasyPrint)
        "css": _REPORT_CSS,
    }

    template = _jinja_env.get_template("report/report.html.j2")
    return template.render(**context)


def _pdf_url_fetcher(url: str) -> dict:
    """Custom WeasyPrint URL fetcher.

    - Serves local files normally.
    - Silently drops external HTTP/HTTPS requests (e.g. Google Fonts CDN) so they
      never raise InvalidValues when base_url is set but the URL is unreachable.
    """
    if url.startswith(("http://", "https://")):
        # Return an empty CSS string so WeasyPrint doesn't choke on external URLs
        return {"string": "", "mime_type": "text/css"}
    from weasyprint.urls import default_url_fetcher
    return default_url_fetcher(url)


def generate_pdf(run_data: dict) -> bytes:
    """Render the report to a PDF byte string using WeasyPrint.

    Args:
        run_data: The full review run result dictionary.

    Returns:
        PDF as bytes.
    """
    from weasyprint import HTML
    html_str = build_html(run_data)
    # Use the templates directory as base_url so WeasyPrint can resolve relative
    # paths (e.g. local font files). External URLs are handled by _pdf_url_fetcher.
    base_url = str(_TEMPLATES_DIR.resolve().as_uri()) + "/"
    return HTML(
        string=html_str,
        base_url=base_url,
        url_fetcher=_pdf_url_fetcher,
    ).write_pdf()
