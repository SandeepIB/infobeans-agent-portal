from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class AppOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None
    route_path: str | None
    icon_svg: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class AppCreate(BaseModel):
    slug: str
    name: str
    description: str | None = None
    route_path: str | None = None
    icon_svg: str | None = None
    is_active: bool = True


class AppUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    route_path: str | None = None
    icon_svg: str | None = None
    is_active: bool | None = None
