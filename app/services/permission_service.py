from __future__ import annotations
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.permission import UserAppPermission
from app.models.user import User


def get_user_apps(db: Session, user: User) -> list[Application]:
    if user.is_admin:
        return db.query(Application).filter(Application.is_active == True).all()  # noqa: E712
    return (
        db.query(Application)
        .join(UserAppPermission, UserAppPermission.app_id == Application.id)
        .filter(
            UserAppPermission.user_id == user.id,
            Application.is_active == True,  # noqa: E712
        )
        .all()
    )


def has_app_permission(db: Session, user: User, app_slug: str) -> bool:
    if user.is_admin:
        app = db.query(Application).filter(
            Application.slug == app_slug,
            Application.is_active == True,  # noqa: E712
        ).first()
        return app is not None
    result = (
        db.query(UserAppPermission)
        .join(Application, Application.id == UserAppPermission.app_id)
        .filter(
            UserAppPermission.user_id == user.id,
            Application.slug == app_slug,
            Application.is_active == True,  # noqa: E712
        )
        .first()
    )
    return result is not None


def grant_permission(db: Session, user_id: int, app_id: int, granted_by_id: int) -> UserAppPermission:
    existing = db.query(UserAppPermission).filter(
        UserAppPermission.user_id == user_id,
        UserAppPermission.app_id == app_id,
    ).first()
    if existing:
        return existing
    perm = UserAppPermission(user_id=user_id, app_id=app_id, granted_by=granted_by_id)
    db.add(perm)
    db.flush()
    return perm


def revoke_permission(db: Session, user_id: int, app_id: int) -> bool:
    perm = db.query(UserAppPermission).filter(
        UserAppPermission.user_id == user_id,
        UserAppPermission.app_id == app_id,
    ).first()
    if perm:
        db.delete(perm)
        db.flush()
        return True
    return False
