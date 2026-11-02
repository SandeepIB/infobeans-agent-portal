from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.application import Application
from app.security.dependencies import require_user
from app.models.user import User
from app import case_study_ppt

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/case-study", tags=["case-study"])

_TMPL_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TMPL_DIR))

# ── Anthropic gateway credentials (shared from ppt_validator) ─────────────────
_ANTHROPIC_KEY = "sk-4XO7Xs7WU8to02MY-yWncQ"
_ANTHROPIC_BASE = "https://gateway.creatingwow.in"
_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """You are an expert business consultant at InfoBeans, specialising in writing
compelling, concise case studies for technology projects. You always respond with
valid JSON matching the schema provided — no additional text, no markdown fences."""

_USER_TEMPLATE = """Create a professional case study using the following project details.

Project Name: {project_name}
Client / Industry: {client_industry}
Project Overview: {overview}
Challenges: {challenges}
Solution: {solution}
Technologies Used: {technologies}
Business Impact: {impact}

Return ONLY a JSON object with this exact schema:
{{
  "executive_summary": "<2-3 sentence paragraph summarising the engagement>",
  "business_challenges": ["<challenge 1>", "<challenge 2>", ...],
  "solution": {{
    "overview": "<1 sentence>",
    "key_points": ["<point 1>", "<point 2>", ...]
  }},
  "technology_stack": ["<tech 1>", "<tech 2>", ...],
  "results": {{
    "headline": "<single impactful headline metric or outcome>",
    "metrics": ["<metric 1>", "<metric 2>", ...]
  }}
}}"""


# ── Request / response schemas ────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    project_name: str
    client_industry: str
    overview: str
    challenges: str
    solution: str
    technologies: str
    impact: str


class PptRequest(BaseModel):
    project_name: str
    client_industry: str
    case_study: dict[str, Any]


# ── UI page ───────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def case_study_page(
    request: Request,
    user: User = Depends(require_user),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "case_study.html", {"user": user}
    )


# ── LLM — generate structured case study ─────────────────────────────────────

@router.post("/api/generate")
async def generate_case_study(
    data: GenerateRequest,
    user: User = Depends(require_user),
) -> dict:
    prompt = _USER_TEMPLATE.format(
        project_name=data.project_name,
        client_industry=data.client_industry,
        overview=data.overview,
        challenges=data.challenges,
        solution=data.solution,
        technologies=data.technologies,
        impact=data.impact,
    )
    payload = {
        "model": _MODEL,
        "max_tokens": 2048,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": _ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{_ANTHROPIC_BASE}/v1/messages",
                headers=headers,
                json=payload,
            )
        if resp.status_code != 200:
            logger.error("LLM error %s: %s", resp.status_code, resp.text[:500])
            raise HTTPException(status_code=502, detail="LLM service error")
        body = resp.json()
        raw = body["content"][0]["text"].strip()
        # Strip markdown fences if model added them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        cs = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error: %s", exc)
        raise HTTPException(status_code=502, detail="LLM returned invalid JSON")
    except httpx.RequestError as exc:
        logger.error("HTTP error calling LLM: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach LLM service")
    return cs


# ── PPT generation ────────────────────────────────────────────────────────────

@router.post("/api/generate-ppt")
async def generate_ppt(
    data: PptRequest,
    user: User = Depends(require_user),
) -> Response:
    try:
        pptx_bytes = case_study_ppt.build(
            data.case_study, data.project_name, data.client_industry
        )
    except Exception as exc:
        logger.error("PPT build error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to build PowerPoint")

    slug = data.project_name.lower().replace(" ", "-")[:40]
    filename = f"case-study-{slug}.pptx"
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── DB seed helper (called at startup) ───────────────────────────────────────

def seed_application(db: Session) -> None:
    # Ensure the case study app has a route set (idempotent on every restart)
    SLUGS = ("case-study-creation", "case-study")
    for slug in SLUGS:
        app = db.query(Application).filter(Application.slug == slug).first()
        if app:
            changed = False
            if app.route_path != "/case-study":
                app.route_path = "/case-study"
                changed = True
            if not app.description:
                app.description = "GenAI-powered case study and PPT generator"
                changed = True
            if changed:
                db.flush()
                logger.info("Updated route_path for '%s'", slug)
            return
    # No matching app found — create it
    new_app = Application(
        slug="case-study",
        name="Case Study Creator",
        description="GenAI-powered case study and PPT generator",
        route_path="/case-study",
        is_active=True,
    )
    db.add(new_app)
    db.flush()
    logger.info("Seeded 'case-study' application record")
