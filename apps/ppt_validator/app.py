"""FROZEN — Legacy FastAPI application entry point.
Only permitted change: adding include_router(...) for new v2 routers.
New routes must go in api/v2/ routers, not here.

Run with:
    uvicorn app:app --host 0.0.0.0 --port 8000 --reload
"""
from __future__ import annotations
import os
from pathlib import Path
from contextlib import asynccontextmanager

# Resolve paths relative to this file so the app works from any working directory
_APP_DIR = Path(__file__).resolve().parent

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")  # load from app dir regardless of cwd

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from db.migrate import run as run_migrations
from api.review import router as v2_review_router
from api.health import router as v2_health_router
from api.prompts import router as v2_prompts_router
from api.rules import router as v2_rules_router
from api.agents import router as v2_agents_router
from api.observability import router as v2_observability_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="IB PPT Validator", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Legacy routes (FROZEN) ────────────────────────────────────────────────

@app.get("/")
def index():
    return {"service": "IB PPT Validator", "version": "1.0.0",
            "ui": "/static/index.html", "v2": "/api/v2/health"}


@app.post("/validate")
async def legacy_validate(file: UploadFile = File(...)):
    """Legacy validation endpoint — calls v2 under the hood."""
    import tempfile, os
    from pathlib import Path
    from services.review_service import ReviewService
    suffix = Path(file.filename or "upload.pptx").suffix or ".pptx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = ReviewService().run(tmp_path, {"review_profile": "customer_presentation", "agents": []})
    finally:
        os.unlink(tmp_path)
    return JSONResponse(content=result)


# ── v2 routers ────────────────────────────────────────────────────────────
app.include_router(v2_review_router)
app.include_router(v2_health_router)
app.include_router(v2_prompts_router)
app.include_router(v2_rules_router)
app.include_router(v2_agents_router)
app.include_router(v2_observability_router)

# ── Static files (legacy UI) ──────────────────────────────────────────────
_static_dir = _APP_DIR / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# ── Frontend dist (production build) ─────────────────────────────────────
_dist_dir = _APP_DIR / "frontend" / "dist"
if _dist_dir.is_dir():
    app.mount("/app", StaticFiles(directory=str(_dist_dir), html=True), name="frontend")
