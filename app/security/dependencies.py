from __future__ import annotations
import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services import permission_service, session_service

logger = logging.getLogger(__name__)

SESSION_COOKIE = "ib_session"


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        session = session_service.get_valid_session(db, token)
        if not session:
            return None
        user = session.user
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        logger.exception("Session lookup error")
        return None


def require_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def require_admin(
    user: User = Depends(require_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user


def require_app_permission(slug: str):
    def _check(
        user: User = Depends(require_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not permission_service.has_app_permission(db, user, slug):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to access this application",
            )
        return user
    return _check


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
