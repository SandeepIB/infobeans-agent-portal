from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str | None = None
    is_admin: bool = False

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class UserUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    is_admin: bool | None = None
