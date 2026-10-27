from __future__ import annotations
import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.models import AuditEvent, User  # noqa: F401 — registers models
from app.routers import admin, api, auth, ppt_validator
from app.security.dependencies import get_current_user_optional

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = pathlib.Path(__file__).resolve().parent
TMPL_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=str(TMPL_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("InfoBeans Agent Hub starting up")
    yield
    logger.info("InfoBeans Agent Hub shutting down")


app = FastAPI(
    title=settings.app_name,
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url="/api/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# ── Session middleware for OAuth state (short-lived signed cookie) ────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="ib_oauth_state",
    max_age=600,
    same_site="lax",
    https_only=settings.session_cookie_secure,
)

# ── Security headers middleware ────────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.session_cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response


# ── Static files ──────────────────────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(admin.router)
app.include_router(ppt_validator.router)


# ── Portal home page ──────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def portal_home(
    request: Request,
    error: str | None = None,
    user: User | None = Depends(get_current_user_optional),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "portal.html",
        {
            "user": user,
            "error": error,
            "app_name": settings.app_name,
        },
    )


# ── Global error handlers ──────────────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            request, "error.html",
            {"status_code": exc.status_code, "detail": exc.detail},
            status_code=exc.status_code,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return templates.TemplateResponse(
            request, "error.html",
            {"status_code": 500, "detail": "An unexpected error occurred"},
            status_code=500,
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
