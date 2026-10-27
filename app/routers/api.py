from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.application import AppOut
from app.schemas.user import UserOut
from app.security.dependencies import require_user
from app.services import permission_service

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(require_user)) -> User:
    return user


@router.get("/apps", response_model=list[AppOut])
def list_user_apps(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list:
    return permission_service.get_user_apps(db, user)
