"""
Case Study Creator: a standalone service behind the InfoBeans Agent Hub.

The hub's reverse proxy (Caddy locally, nginx in production) signs the user in,
checks access to 'case-study-creation', and passes the identity as headers:
X-Auth-User-Id, X-Auth-Email, X-Auth-Name. This service trusts only those headers
and listens on 127.0.0.1, so it cannot be reached without going through the hub.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
from types import SimpleNamespace
from typing import Any
from urllib.parse import unquote

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

import case_study_ppt

BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

LLM_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://gateway.creatingwow.in")
LLM_MODEL = os.getenv("CASE_STUDY_LLM_MODEL", "claude-sonnet-5")

logger = logging.getLogger("case_study")

SYSTEM_PROMPT = """You are an expert business consultant at InfoBeans, specialising in writing
compelling, concise case studies for technology projects. You always respond with
valid JSON matching the schema provided — no additional text, no markdown fences."""

USER_TEMPLATE = """Create a professional case study using the following project details.

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


# ── Identity from the hub ─────────────────────────────────────────────────────

def current_user(request: Request) -> SimpleNamespace:
    """The signed-in hub user, from the headers the proxy sets. No headers = not via the hub."""
    email = request.headers.get("x-auth-email")
    if not email:
        raise HTTPException(status_code=401, detail="Not signed in")
    name = unquote(request.headers.get("x-auth-name", "")) or email
    return SimpleNamespace(id=request.headers.get("x-auth-user-id"), email=email, name=name)


# ── Schemas ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=200)
    client_industry: str = Field(min_length=1, max_length=200)
    overview: str = Field(min_length=1, max_length=5000)
    challenges: str = Field(min_length=1, max_length=5000)
    solution: str = Field(min_length=1, max_length=5000)
    technologies: str = Field(min_length=1, max_length=2000)
    impact: str = Field(min_length=1, max_length=5000)


class PptRequest(BaseModel):
    project_name: str = Field(min_length=1, max_length=200)
    client_industry: str = Field(min_length=1, max_length=200)
    case_study: dict[str, Any]


# ── LLM call (isolated so tests can replace it) ──────────────────────────────

def extract_text(body: dict) -> str:
    """Join the reply's text blocks, skipping thinking blocks."""
    blocks = body.get("content") or []
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


async def call_llm(prompt: str) -> str:
    if not LLM_API_KEY:
        raise HTTPException(status_code=502, detail="The case study service is not configured")
    payload = {
        "model": LLM_MODEL,
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{LLM_BASE_URL.rstrip('/')}/v1/messages", headers=headers, json=payload)
    except httpx.RequestError as exc:
        logger.error("Could not reach LLM service: %s", exc)
        raise HTTPException(status_code=502, detail="Could not reach LLM service")
    if resp.status_code != 200:
        logger.error("LLM error %s: %s", resp.status_code, resp.text[:500])
        raise HTTPException(status_code=502, detail="LLM service error")
    try:
        body = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="LLM returned an unexpected response")
    text = extract_text(body)
    if not text:
        logger.error("No text in LLM reply: content_types=%s stop_reason=%s",
                     [b.get("type") for b in body.get("content") or []], body.get("stop_reason"))
        raise HTTPException(status_code=502, detail="LLM returned an unexpected response")
    return text


def parse_case_study(raw: str) -> dict:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="LLM returned invalid JSON")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="LLM returned invalid JSON")
    return data


# ── Routes (same URLs as in the old hub) ─────────────────────────────────────

router = APIRouter(prefix="/case-study")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def page(request: Request, user: SimpleNamespace = Depends(current_user)) -> HTMLResponse:
    return templates.TemplateResponse(request, "case_study.html", {"user": user})


@router.post("/api/generate")
async def generate(data: GenerateRequest, user: SimpleNamespace = Depends(current_user)) -> dict:
    raw = await call_llm(USER_TEMPLATE.format(**data.model_dump()))
    logger.info("Case study generated for %s", user.email)
    return parse_case_study(raw)


@router.post("/api/generate-ppt")
def generate_ppt(data: PptRequest, user: SimpleNamespace = Depends(current_user)) -> Response:
    try:
        pptx_bytes = case_study_ppt.build(data.case_study, data.project_name, data.client_industry)
    except Exception:
        logger.exception("PPT build failed")
        raise HTTPException(status_code=500, detail="Failed to build PowerPoint")
    slug = data.project_name.lower().replace(" ", "-")[:40] or "untitled"
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="case-study-{slug}.pptx"'},
    )


app = FastAPI(title="Case Study Creator", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/case-study/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(router)