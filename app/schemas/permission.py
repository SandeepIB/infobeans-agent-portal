from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel


class PermissionOut(BaseModel):
    id: int
    user_id: int
    app_id: int
    granted_by: int | None
    granted_at: datetime

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    user_id: int
    app_id: int
