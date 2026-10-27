from __future__ import annotations
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.session import AppSession
from app.models.user import User


def create_session(db: Session, user: User, ip_address: str | None, user_agent: str | None) -> str:
    token = secrets.token_urlsafe(64)
    expires = datetime.now(timezone.utc) + timedelta(seconds=settings.session_max_age_seconds)
    session = AppSession(
        session_token=token,
        user_id=user.id,
        expires_at=expires.replace(tzinfo=None),
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent else None,
    )
    db.add(session)
    db.flush()
    return token


def get_valid_session(db: Session, token: str) -> AppSession | None:
    now = datetime.utcnow()
    session = (
        db.query(AppSession)
        .filter(
            AppSession.session_token == token,
            AppSession.is_revoked == False,  # noqa: E712
            AppSession.expires_at > now,
        )
        .first()
    )
    if session:
        session.last_activity_at = now
        db.flush()
    return session


def revoke_session(db: Session, token: str) -> None:
    session = db.query(AppSession).filter(AppSession.session_token == token).first()
    if session:
        session.is_revoked = True
        db.flush()


def revoke_all_user_sessions(db: Session, user_id: int) -> None:
    db.query(AppSession).filter(
        AppSession.user_id == user_id,
        AppSession.is_revoked == False,  # noqa: E712
    ).update({"is_revoked": True})
    db.flush()
