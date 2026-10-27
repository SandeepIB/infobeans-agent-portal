from __future__ import annotations
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.security.dependencies import SESSION_COOKIE, get_client_ip, get_current_user_optional
from app.services import audit_service, session_service
from app.services.google_auth import (
    exchange_code,
    extract_verified_email,
    get_authorization_url,
    get_jwks,
    verify_id_token,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

_STATE_KEY = "oauth_state"


@router.get("/auth/google/login")
async def google_login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    request.session[_STATE_KEY] = state
    url = await get_authorization_url(state)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/auth/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if error:
        logger.warning("OAuth error from Google: %s", error)
        return RedirectResponse(url="/?error=oauth_error", status_code=status.HTTP_302_FOUND)

    stored_state = request.session.pop(_STATE_KEY, None)
    if not stored_state or stored_state != state:
        logger.warning("OAuth state mismatch")
        return RedirectResponse(url="/?error=state_mismatch", status_code=status.HTTP_302_FOUND)

    if not code:
        return RedirectResponse(url="/?error=missing_code", status_code=status.HTTP_302_FOUND)

    try:
        token = await exchange_code(code)
        id_token_str = token.get("id_token")
        if not id_token_str:
            raise ValueError("No id_token in response")

        jwks = await get_jwks()
        claims = verify_id_token(id_token_str, jwks)
        email = extract_verified_email(claims)
        google_sub = str(claims.get("sub", ""))
        display_name = claims.get("name") or email.split("@")[0]

    except Exception:
        logger.exception("Token verification failed")
        return RedirectResponse(url="/?error=auth_failed", status_code=status.HTTP_302_FOUND)

    user = db.query(User).filter(User.email == email).first()

    if not user:
        audit_service.log_event(
            db, "login_rejected_not_allowlisted",
            actor_email=email,
            ip_address=get_client_ip(request),
            details={"reason": "not_in_allowlist"},
        )
        return RedirectResponse(url="/?error=not_authorised", status_code=status.HTTP_302_FOUND)

    if not user.is_active:
        audit_service.log_event(
            db, "login_rejected_inactive",
            actor_email=email,
            actor_user_id=user.id,
            ip_address=get_client_ip(request),
        )
        return RedirectResponse(url="/?error=account_inactive", status_code=status.HTTP_302_FOUND)

    if not user.google_subject:
        user.google_subject = google_sub
    if not user.display_name:
        user.display_name = display_name

    from datetime import datetime
    user.last_login_at = datetime.utcnow()

    session_token = session_service.create_session(
        db, user,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    audit_service.log_event(
        db, "login_success",
        actor_user_id=user.id,
        actor_email=email,
        ip_address=get_client_ip(request),
    )

    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=settings.session_max_age_seconds,
        httponly=settings.session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    return response


@router.post("/logout")
@router.get("/logout")
async def logout(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> RedirectResponse:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session_service.revoke_session(db, token)
    if user:
        audit_service.log_event(
            db, "logout",
            actor_user_id=user.id,
            actor_email=user.email,
            ip_address=get_client_ip(request),
        )
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
