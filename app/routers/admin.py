from __future__ import annotations
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.application import Application
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.application import AppCreate, AppOut, AppUpdate
from app.schemas.permission import PermissionCreate, PermissionOut
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.security.dependencies import require_admin
from app.services import audit_service, permission_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

import pathlib
_TMPL_DIR = pathlib.Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TMPL_DIR))


# ── Admin UI pages ──────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    user_count = db.query(User).count()
    app_count = db.query(Application).count()
    recent_events = (
        db.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(
        request, "admin/dashboard.html",
        {"user": admin, "user_count": user_count,
         "app_count": app_count, "recent_events": recent_events, "active": "dashboard"},
    )


@router.get("/users", response_class=HTMLResponse)
def admin_users_page(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    users = db.query(User).order_by(User.created_at.desc()).all()
    apps = db.query(Application).filter(Application.is_active == True).all()  # noqa: E712
    apps_data = [{"id": a.id, "name": a.name, "slug": a.slug} for a in apps]
    return templates.TemplateResponse(
        request, "admin/users.html",
        {"user": admin, "users": users, "apps": apps_data, "active": "users"},
    )


@router.get("/apps", response_class=HTMLResponse)
def admin_apps_page(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    apps = db.query(Application).order_by(Application.name).all()
    return templates.TemplateResponse(
        request, "admin/apps.html",
        {"user": admin, "apps": apps, "active": "apps"},
    )


@router.get("/permissions", response_class=HTMLResponse)
def admin_permissions_page(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    from app.models.permission import UserAppPermission
    perms = (
        db.query(UserAppPermission)
        .join(User, User.id == UserAppPermission.user_id)
        .join(Application, Application.id == UserAppPermission.app_id)
        .order_by(User.email)
        .all()
    )
    users = db.query(User).filter(User.is_active == True).order_by(User.email).all()  # noqa: E712
    apps = db.query(Application).filter(Application.is_active == True).order_by(Application.name).all()  # noqa: E712
    return templates.TemplateResponse(
        request, "admin/permissions.html",
        {"user": admin, "perms": perms, "users": users, "apps": apps, "active": "permissions"},
    )


# ── User management API ──────────────────────────────────────────────────────

@router.get("/api/users", response_model=list[UserOut])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list:
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/api/users", response_model=UserOut, status_code=201)
def create_user(
    data: UserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    user = User(
        email=data.email,
        display_name=data.display_name,
        is_admin=data.is_admin,
        is_active=True,
    )
    db.add(user)
    db.flush()
    audit_service.log_event(
        db, "user_created",
        actor_user_id=admin.id, actor_email=admin.email,
        target_user_id=user.id,
        details={"email": user.email},
    )
    return user


@router.get("/api/users/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/api/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == admin.id and data.is_admin is False:
        raise HTTPException(status_code=400, detail="Cannot remove your own admin privilege")
    if data.display_name is not None:
        user.display_name = data.display_name
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    db.flush()
    audit_service.log_event(
        db, "user_updated",
        actor_user_id=admin.id, actor_email=admin.email,
        target_user_id=user.id,
        details={"changes": data.model_dump(exclude_none=True)},
    )
    return user


@router.get("/api/users/{user_id}/permissions")
def get_user_permissions(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list:
    from app.models.permission import UserAppPermission
    perms = db.query(UserAppPermission).filter(UserAppPermission.user_id == user_id).all()
    return [{"id": p.id, "user_id": p.user_id, "app_id": p.app_id, "granted_at": p.granted_at.isoformat()} for p in perms]


# ── Application management API ───────────────────────────────────────────────

@router.get("/api/apps", response_model=list[AppOut])
def list_apps(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list:
    return db.query(Application).order_by(Application.name).all()


@router.post("/api/apps", response_model=AppOut, status_code=201)
def create_app(
    data: AppCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Application:
    existing = db.query(Application).filter(Application.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Application with this slug already exists")
    app = Application(**data.model_dump())
    db.add(app)
    db.flush()
    audit_service.log_event(
        db, "app_created",
        actor_user_id=admin.id, actor_email=admin.email,
        target_app_id=app.id,
        details={"slug": app.slug, "name": app.name},
    )
    return app


@router.patch("/api/apps/{app_id}", response_model=AppOut)
def update_app(
    app_id: int,
    data: AppUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Application:
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(app, field, value)
    db.flush()
    audit_service.log_event(
        db, "app_updated",
        actor_user_id=admin.id, actor_email=admin.email,
        target_app_id=app.id,
    )
    return app


# ── Permission management API ─────────────────────────────────────────────────

@router.post("/api/permissions", response_model=PermissionOut, status_code=201)
def grant_permission(
    data: PermissionCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> object:
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    app = db.query(Application).filter(Application.id == data.app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    perm = permission_service.grant_permission(db, data.user_id, data.app_id, admin.id)
    audit_service.log_event(
        db, "permission_granted",
        actor_user_id=admin.id, actor_email=admin.email,
        target_user_id=data.user_id, target_app_id=data.app_id,
    )
    return perm


@router.delete("/api/permissions", status_code=204)
def revoke_permission(
    data: PermissionCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    revoked = permission_service.revoke_permission(db, data.user_id, data.app_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Permission not found")
    audit_service.log_event(
        db, "permission_revoked",
        actor_user_id=admin.id, actor_email=admin.email,
        target_user_id=data.user_id, target_app_id=data.app_id,
    )
